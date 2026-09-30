import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

# ==============================================================================
# 1. PARAMETERS & CONFIGURATION
# ==============================================================================
GROUP_ORDER = 13       # Order of the cyclic subgroup (r = 13)
EXPECTED_KEY = 7      # Secret private key d = 7 (Q = [7]G)
SHOTS = 4096           # High shot count for QPU noise mitigation

print("=" * 75)
print("   12-QUBIT SHOR'S DISCRETE LOG / REAL QPU EXECUTION (r = 13)")
print("=" * 75)

# =====================================================================
# 4. Execute on Real IBM Quantum Hardware
# =====================================================================
print("Connecting to IBM Quantum Platform...")
service = QiskitRuntimeService(channel="ibm_quantum_platform")

# Select the least busy operational backend with at least 12 qubits
backend = service.least_busy(operational=True, simulator=False, min_num_qubits=12)
print(f"[+] Connected Target Hardware : {backend.name}")
print(f"[+] Total Qubits Available   : {backend.num_qubits}")
print("=" * 75)

# ==============================================================================
# 2. CIRCUIT SETUP
# ==============================================================================
c1 = QuantumRegister(4, name="c1")
c2 = QuantumRegister(4, name="c2")
tgt = QuantumRegister(4, name="tgt")

cl1 = ClassicalRegister(4, name="meas_c1")
cl2 = ClassicalRegister(4, name="meas_c2")

qc = QuantumCircuit(c1, c2, tgt, cl2, cl1)

# Step A: Initialize counting registers in uniform superposition
qc.h(c1)
qc.h(c2)

# Step B: Construct Modular Shift Oracle over Z_13
def build_mod13_shift_gate(shift):
    matrix = np.zeros((16, 16))
    for x in range(16):
        if x < GROUP_ORDER:
            new_x = (x + shift) % GROUP_ORDER
        else:
            new_x = x  # Leave padding states unchanged
        matrix[new_x, x] = 1.0
    return UnitaryGate(matrix, label=f"+{shift} mod 13")

# Apply controlled shifts for c1 register (weight 1 * 2^i mod 13)
for i in range(4):
    shift_val = (1 * (2**i)) % GROUP_ORDER
    gate = build_mod13_shift_gate(shift_val).control(1)
    qc.append(gate, [c1[i]] + list(tgt))

# Apply controlled shifts for c2 register (weight d * 2^i mod 13)
for i in range(4):
    shift_val = (EXPECTED_KEY * (2**i)) % GROUP_ORDER
    gate = build_mod13_shift_gate(shift_val).control(1)
    qc.append(gate, [c2[i]] + list(tgt))

# Step C: Standard Inverse QFT
def apply_iqft(circuit, reg):
    n = len(reg)
    for i in range(n // 2):
        circuit.swap(reg[i], reg[n - 1 - i])
    for j in range(n):
        for m in range(j):
            circuit.cp(-np.pi / (2 ** (j - m)), reg[m], reg[j])
        circuit.h(reg[j])

apply_iqft(qc, c1)
apply_iqft(qc, c2)

# Step D: Measurement
qc.measure(c2, cl2)
qc.measure(c1, cl1)

# ==============================================================================
# 3. HARDWARE TRANSPILATION & QPU SUBMISSION
# ==============================================================================
print("\n[+] Transpiling circuit for target QPU backend...")
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

# Parse bitstrings from SamplerV2 DataBin
counts_c2 = pub_result.data.meas_c2.get_counts()
counts_c1 = pub_result.data.meas_c1.get_counts()

# Reconstruct combined counts
raw_counts = {}
for b2, c2_cnt in counts_c2.items():
    for b1, c1_cnt in counts_c1.items():
        combined_key = f"{b2} {b1}"
        raw_counts[combined_key] = raw_counts.get(combined_key, 0) + min(c2_cnt, c1_cnt)

# ==============================================================================
# 4. POST-PROCESSING & KEY RECOVERY
# ==============================================================================
parsed_results = []
for bitstr, count in raw_counts.items():
    v_str, u_str = bitstr.split()
    
    # Reverse bitstring ([::-1]) to convert Qiskit little-endian format
    v_val = int(v_str[::-1], 2)
    u_val = int(u_str[::-1], 2)
    prob = (count / SHOTS) * 100
    
    parsed_results.append((bitstr, v_val, u_val, count, prob))

parsed_results.sort(key=lambda x: x[3], reverse=True)

print("\n" + "=" * 75)
print(f" {'RAW BITSTRING':<15} | {'PAIR (v, u)':<12} | {'SHOTS':<8} | {'PROBABILITY':<12} | {'INTERFERENCE TYPE'}")
print("=" * 75)

top_peaks = []
for bitstr, v_val, u_val, count, prob in parsed_results[:12]:
    if v_val == 0 and u_val == 0:
        itype = "Trivial Phase Zero (Skip)"
    elif u_val < GROUP_ORDER and v_val < GROUP_ORDER:
        itype = "Constructive Signal Peak"
        top_peaks.append((v_val, u_val, count))
    else:
        itype = "Noise / Leakage (u,v >= 13)"
        
    print(f" {bitstr:<15} | ({v_val:2d}, {u_val:2d}){' ':<5} | {count:<8} | {prob:6.2f}%      | {itype}")

print("=" * 75)

# Classical Inversion Block
print("\n--- CLASSICAL POST-PROCESSING & INVERSION VERIFICATION ---")

raw_d_inv_candidates = []
for v_val, u_val, count in top_peaks:
    if v_val == 0 or u_val == 0:
        continue

    v_inv = pow(v_val, -1, GROUP_ORDER)
    d_inv = (u_val * v_inv) % GROUP_ORDER

    raw_d_inv_candidates.append((d_inv, count))
    print(f"Peak ({v_val:2d}, {u_val:2d}): Phase ratio u/v mod 13 ==> d^-1 = {d_inv:2d} (Weight: {count} shots)")

if raw_d_inv_candidates:
    vote_scores = {}
    for d_inv_val, count in raw_d_inv_candidates:
        vote_scores[d_inv_val] = vote_scores.get(d_inv_val, 0) + count

    best_d_inv = max(vote_scores, key=vote_scores.get)
    derived_d = pow(best_d_inv, -1, GROUP_ORDER)

    print("\n---------------------------------------------------------------------------")
    print(f" 1. Quantum Phase Measurement Output (d^-1)  : {best_d_inv}")
    print(f" 2. Classical Inversion Step                : d = ({best_d_inv})^-1 mod 13 = {derived_d}")
    print(f" 3. Mathematical Identity Check             : {EXPECTED_KEY} * {best_d_inv} = {EXPECTED_KEY * best_d_inv} === 1 (mod 13)")
    print("---------------------------------------------------------------------------")
    print(f" SUCCESS: Recovered Secret Private Key d = {derived_d}")
    print(f" Matches Expected Key (d = {EXPECTED_KEY})? : {derived_d == EXPECTED_KEY}")
    print("---------------------------------------------------------------------------")