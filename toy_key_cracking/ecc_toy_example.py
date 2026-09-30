import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator

# ==============================================================================
# 1. SETUP & PARAMETERS
# ==============================================================================
GROUP_ORDER = 3
EXPECTED_KEY = 2
SHOTS = 1024

print("=" * 70)
print("       SHOR'S DISCRETE LOG / TOY ECC KEY RECOVERY DEMO")
print("=" * 70)
print(f" Group Order (r) : {GROUP_ORDER}")
print(f" Target Relation : Q = [d]G  where secret key d = {EXPECTED_KEY}")
print("=" * 70)

# ==============================================================================
# 2. CIRCUIT CONSTRUCTION
# ==============================================================================
c1 = QuantumRegister(2, name="c1")
c2 = QuantumRegister(2, name="c2")
tgt = QuantumRegister(2, name="tgt")

cl1 = ClassicalRegister(2, name="meas_c1")
cl2 = ClassicalRegister(2, name="meas_c2")

qc = QuantumCircuit(c1, c2, tgt, cl2, cl1)

# Step A: Uniform superposition
qc.h(c1)
qc.h(c2)

# Step B: Oracle Function (Computes |a*G + b*Q> mod 3 into target)
for i in range(2):
    qc.cx(c1[i], tgt[i])
    qc.cx(c2[i], tgt[(i + 1) % 2])

# Step C: Inverse QFT on c1
qc.swap(c1[0], c1[1])
qc.h(c1[0])
qc.cp(-np.pi / 2, c1[0], c1[1])
qc.h(c1[1])

# Step D: Inverse QFT on c2
qc.swap(c2[0], c2[1])
qc.h(c2[0])
qc.cp(-np.pi / 2, c2[0], c2[1])
qc.h(c2[1])

# Step E: Measurement
qc.measure(c2, cl2)
qc.measure(c1, cl1)

# ==============================================================================
# 3. SIMULATION EXECUTION
# ==============================================================================
simulator = AerSimulator()
raw_counts = simulator.run(qc, shots=SHOTS).result().get_counts()

# ==============================================================================
# 4. FORMATTED OUTPUT & POST-PROCESSING TABLE
# ==============================================================================
print("\n" + "=" * 70)
print(f" {'RAW BITSTRING':<15} | {'PAIR (v, u)':<12} | {'SHOTS':<8} | {'PROBABILITY':<12} | {'INTERFERENCE TYPE'}")
print("=" * 70)

parsed_results = []
for bitstr, count in raw_counts.items():
    if " " in bitstr:
        v_str, u_str = bitstr.split()
    else:
        v_str, u_str = bitstr[:2], bitstr[2:]
        
    v_val = int(v_str, 2)
    u_val = int(u_str, 2)
    prob = (count / SHOTS) * 100
    
    parsed_results.append((bitstr, v_val, u_val, count, prob))

parsed_results.sort(key=lambda x: x[3], reverse=True)

for bitstr, v_val, u_val, count, prob in parsed_results:
    if v_val == 0 and u_val == 0:
        itype = "Trivial Phase Zero (Skip)"
    elif u_val < GROUP_ORDER and v_val < GROUP_ORDER:
        itype = "Constructive Signal Peak"
    else:
        itype = "Spectral Leakage (u,v >= r)"
        
    print(f" {bitstr:<15} | ({v_val}, {u_val}){' ':<7} | {count:<8} | {prob:6.2f}%      | {itype}")

print("=" * 70)

# ==============================================================================
# 5. CLASSICAL KEY DERIVATION MATH
# ==============================================================================
print("\n--- CLASSICAL POST-PROCESSING & KEY RECOVERY ---")

candidates = []
for bitstr, v_val, u_val, count, prob in parsed_results:
    if v_val == 0 and u_val == 0:
        continue
    if v_val >= GROUP_ORDER or u_val >= GROUP_ORDER:
        continue

    # IQFT phase relation: u - d*v = 0 mod r ==> d = (u * v^-1) mod r
    v_inv = pow(v_val, -1, GROUP_ORDER)
    derived_d = (u_val * v_inv) % GROUP_ORDER

    candidates.append((derived_d, count))
    print(f"Peak ({v_val}, {u_val}): Solving {u_val} - d*({v_val}) = 0 mod 3  ==>  d = {derived_d} (Weight: {count} shots)")

if candidates:
    vote_scores = {}
    for d_val, count in candidates:
        vote_scores[d_val] = vote_scores.get(d_val, 0) + count

    best_d = max(vote_scores, key=vote_scores.get)

    print("\n------------------------------------------------")
    print(f" SUCCESS: Classical post-processing derived private key d = {best_d}")
    print(f" Matches Expected Secret Key? : {best_d == EXPECTED_KEY}")
    print("------------------------------------------------")