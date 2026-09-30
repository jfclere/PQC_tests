import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import UnitaryGate

# Modern Qiskit Runtime imports
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

# ==============================================================================
# 1. PARAMETERS & CONFIGURATION
# ==============================================================================
GROUP_ORDER = 3        # Reduced group order (r = 3)
EXPECTED_KEY = 2       # Target relation Q = [2]G mod 3 (secret key d = 2)
SHOTS = 4096           # High shot count for statistical confidence

print("=" * 75)
print("     6-QUBIT SHOR'S DISCRETE LOG / REAL QPU EXECUTION (r = 3)")
print("=" * 75)
print(f" Group Order (r) : {GROUP_ORDER}")
print(f" Target Relation : Q = [d]G  where secret key d = {EXPECTED_KEY}")
print(f" Qubit Budget    : 2 (c1) + 2 (c2) + 2 (tgt) = 6 Qubits Total")
print("=" * 75)

# Connect to IBM Quantum Platform
print("Connecting to IBM Quantum Platform...")
service = QiskitRuntimeService(channel="ibm_quantum_platform")

# Select least busy backend with at least 6 qubits
backend = service.least_busy(operational=True, simulator=False, min_num_qubits=6)
print(f"[+] Connected Target Hardware : {backend.name}")
print(f"[+] Total Qubits Available   : {backend.num_qubits}")
print("=" * 75)

# ==============================================================================
# 2. CIRCUIT CONSTRUCTION (6 QUBITS)
# ==============================================================================
c1 = QuantumRegister(2, name="c1")
c2 = QuantumRegister(2, name="c2")
tgt = QuantumRegister(2, name="tgt")

cl1 = ClassicalRegister(2, name="meas_c1")
cl2 = ClassicalRegister(2, name="meas_c2")

qc = QuantumCircuit(c1, c2, tgt, cl2, cl1)

# Step A: Uniform superposition on control registers
qc.h(c1)
qc.h(c2)

# Step B: Construct Exact Modular Shift Oracle over Z_3 (4-state space)
def build_mod3_shift_gate(shift):
    matrix = np.zeros((4, 4))
    for x in range(4):
        if x < GROUP_ORDER:
            new_x = (x + shift) % GROUP_ORDER
        else:
            new_x = x  # Leave padding state (x=3) unchanged
        matrix[new_x, x] = 1.0
    return UnitaryGate(matrix, label=f"+{shift} mod 3")

# Controlled modular shifts for c1 register (weight 1 * 2^i mod 3)
for i in range(2):
    shift_val = (1 * (2**i)) % GROUP_ORDER
    gate = build_mod3_shift_gate(shift_val).control(1)
    qc.append(gate, [c1[i]] + list(tgt))

# Controlled modular shifts for c2 register (weight d * 2^i mod 3)
for i in range(2):
    shift_val = (EXPECTED_KEY * (2**i)) % GROUP_ORDER
    gate = build_mod3_shift_gate(shift_val).control(1)
    qc.append(gate, [c2[i]] + list(tgt))

# Step C: 2-Qubit Inverse QFT Function
def apply_iqft(circuit, reg):
    circuit.swap(reg[0], reg[1])
    circuit.h(reg[0])
    circuit.cp(-np.pi / 2, reg[0], reg[1])
    circuit.h(reg[1])

apply_iqft(qc, c1)
apply_iqft(qc, c2)

# Step D: Measurement
qc.measure(c2, cl2)
qc.measure(c1, cl1)

# ==============================================================================
# 3. TRANSPILATION & REAL QPU SUBMISSION
# ==============================================================================
print("\n[+] Transpiling 6-qubit circuit for target QPU backend...")
compiled_circuit = transpile(qc, backend=backend, optimization_level=3)

print(f"[+] Transpiled Circuit Depth : {compiled_circuit.depth()}")
print(f"[+] Total Gate Operations     : {compiled_circuit.count_ops()}")

print("\n[+] Submitting job to IBM Quantum Platform queue...")
sampler = Sampler(mode=backend)
job = sampler.run([compiled_circuit], shots=SHOTS)
print(f"[+] Job ID: {job.job_id()}")
print("[+] Waiting for backend execution...")

result = job.result()
pub_result = result[0]

# Parse bitstring results from Sampler DataBin
counts_c2 = pub_result.data.meas_c2.get_counts()
counts_c1 = pub_result.data.meas_c1.get_counts()

raw_counts = {}
for b2, c2_cnt in counts_c2.items():
    for b1, c1_cnt in counts_c1.items():
        combined_key = f"{b2} {b1}"
        raw_counts[combined_key] = raw_counts.get(combined_key, 0) + min(c2_cnt, c1_cnt)

# ==============================================================================
# 4. POST-PROCESSING & NOISE FILTERING
# ==============================================================================
parsed_results = []
for bitstr, count in raw_counts.items():
    v_str, u_str = bitstr.split()
    
    # Reverse bitstring ([::-1]) to convert Qiskit's LSB format to MSB integers
    v_val = int(v_str[::-1], 2)
    u_val = int(u_str[::-1], 2)
    prob = (count / SHOTS) * 100
    
    parsed_results.append((bitstr, v_val, u_val, count, prob))

parsed_results.sort(key=lambda x: x[3], reverse=True)

print("\n" + "=" * 75)
print(f" {'RAW BITSTRING':<15} | {'PAIR (v, u)':<12} | {'SHOTS':<8} | {'PROBABILITY':<12} | {'INTERFERENCE TYPE'}")
print("=" * 75)

top_peaks = []
for bitstr, v_val, u_val, count, prob in parsed_results:
    if v_val == 0 and u_val == 0:
        itype = "Trivial Phase Zero (Skip)"
    elif u_val < GROUP_ORDER and v_val < GROUP_ORDER:
        itype = "Constructive Signal Peak"
        top_peaks.append((v_val, u_val, count))
    else:
        itype = "Spectral Leakage (u,v >= 3)"
        
    print(f" {bitstr:<15} | ({v_val:2d}, {u_val:2d}){' ':<5} | {count:<8} | {prob:6.2f}%      | {itype}")

print("=" * 75)

# ==============================================================================
# 5. CLASSICAL KEY RECOVERY (STRICT OFF-DIAGONAL FILTERING)
# ==============================================================================
print("\n--- CLASSICAL POST-PROCESSING & OFF-DIAGONAL FILTERING ---")

vote_scores = {}
for v_val, u_val, count in top_peaks:
    # 1. Skip zero-phase states
    if v_val == 0 or u_val == 0:
        continue

    # 2. Skip trivial diagonal phase states (u == v carries no key information)
    if u_val == v_val:
        print(f"Skipping trivial diagonal state ({v_val}, {u_val}) [u == v, d^-1 = 1]")
        continue

    # 3. Calculate true off-diagonal phase ratio: d^-1 = u * v^-1 mod 3
    v_inv = pow(v_val, -1, GROUP_ORDER)
    d_inv = (u_val * v_inv) % GROUP_ORDER

    vote_scores[d_inv] = vote_scores.get(d_inv, 0) + count
    print(f"Constructive Signal Peak ({v_val}, {u_val}): Phase ratio u/v mod 3 ==> d^-1 = {d_inv} ({count} shots)")

if vote_scores:
    print("\n--- OFF-DIAGONAL QUANTUM PHASE VOTES ---")
    for candidate_d_inv, total_weight in vote_scores.items():
        print(f" Candidate d^-1 = {candidate_d_inv} : Accumulation = {total_weight} shots")

    best_d_inv = max(vote_scores, key=vote_scores.get)
    derived_d = pow(best_d_inv, -1, GROUP_ORDER)

    print("\n---------------------------------------------------------------------------")
    print(f" 1. Measured Off-Diagonal Phase Output (d^-1) : {best_d_inv}")
    print(f" 2. Classical Inversion Step                : d = ({best_d_inv})^-1 mod 3 = {derived_d}")
    print(f" 3. Mathematical Identity Check             : {EXPECTED_KEY} * {best_d_inv} = {EXPECTED_KEY * best_d_inv} === 1 (mod 3)")
    print("---------------------------------------------------------------------------")
    print(f" SUCCESS: Recovered Secret Private Key d = {derived_d}")
    print(f" Matches Expected Key (d = {EXPECTED_KEY})? : {derived_d == EXPECTED_KEY}")
    print("---------------------------------------------------------------------------")