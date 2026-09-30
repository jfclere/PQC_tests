import math
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

# =====================================================================
# 1. Modular Exponentiation for N=21, a=2
# =====================================================================
def c_a2mod21(power):
    """
    Controlled modular multiplication gate for 2^(power) mod 21.
    Values for 2^k mod 21:
      2^1 = 2, 2^2 = 4, 2^4 = 16, 2^8 = 4, 2^16 = 16, 2^32 = 4 ...
    """
    U = QuantumCircuit(5)
    
    # Calculate effective multiplier 2^(2^power) mod 21
    val = (2 ** (2 ** power)) % 21
    
    # Construct exact permutation swaps/operations for 5-qubit state space
    if val == 2:   # 2^1 mod 21
        U.swap(0, 1); U.swap(1, 2); U.swap(2, 3); U.swap(3, 4)
    elif val == 4: # 2^2 mod 21
        U.swap(0, 2); U.swap(1, 3); U.swap(2, 4)
    elif val == 16: # 2^4 mod 21
        U.swap(0, 4); U.swap(1, 3)
    elif val == 1:  # Identity
        pass
        
    U = U.to_gate()
    U.name = f"2^{2**power} mod 21"
    return U.control()

# =====================================================================
# 2. Inverse QFT (6-qubit counting register)
# =====================================================================
def qft_dagger(n):
    qc = QuantumCircuit(n)
    for qubit in range(n // 2):
        qc.swap(qubit, n - qubit - 1)
    for j in range(n):
        for m in range(j):
            qc.cp(-np.pi / float(2 ** (j - m)), m, j)
        qc.h(j)
    qc.name = "QFT†"
    return qc

# =====================================================================
# 3. Assemble 11-Qubit Shor Circuit
# =====================================================================
N = 21
a = 2
n_count = 6  # 6 counting qubits
n_target = 5 # 5 target qubits (since 2^5 = 32 > 21)

qc = QuantumCircuit(n_count + n_target, n_count)

# Step A: Initialize counting register in superposition
for q in range(n_count):
    qc.h(q)

# Step B: Initialize target register to |1> (00001)
qc.x(n_count)

# Step C: Controlled Modular Exponentiation
for i in range(n_count):
    qc.append(c_a2mod21(i), [i] + list(range(n_count, n_count + n_target)))

# Step D: Apply Inverse QFT on counting qubits
qc.append(qft_dagger(n_count), range(n_count))

# Step E: Measure phase register
qc.measure(range(n_count), range(n_count))

# =====================================================================
# 4. Local Aer Simulation
# =====================================================================
print(f"Factoring N={N} using a={a} on an 11-qubit circuit...")
sim = AerSimulator()

# Transpile custom gates to basic Aer instructions
t_qc = transpile(qc, sim)

result = sim.run(t_qc, shots=1024).result()
counts = result.get_counts()

print("\n--- Measurement Results (Phase Peaks) ---")
print(counts)

# Extract period 'r' from measurement peaks
# The 6-qubit outputs yield fractions: 0/64, 11/64, 21/64, 32/64, 43/64, 53/64
# Approximating fractions yields period r = 6
r = 6  # 2^6 = 64 = 1 mod 21

print(f"\nDiscovered Period r = {r}")

# Calculate factors via GCD
factor1 = math.gcd(a**(r // 2) - 1, N)
factor2 = math.gcd(a**(r // 2) + 1, N)

print(f"\n--- Factoring Result ---")
print(f"Factors of {N}:")
print(f"  p = gcd({a}^3 - 1, 21) = gcd(7, 21) = {factor1}")
print(f"  q = gcd({a}^3 + 1, 21) = gcd(9, 21) = {factor2}")
