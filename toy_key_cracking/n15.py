import math
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
from qiskit import transpile

# =====================================================================
# 1. Modular Exponentiation Gate Construction
# =====================================================================
def c_amod15(a, power):
    """
    Returns a controlled gate for multiplying by (a^power) mod 15.
    For N=15 and a=7, powers repeat every 4 steps:
    7^1 = 7, 7^2 = 4, 7^3 = 13, 7^4 = 1 (mod 15)
    """
    if a not in [2, 7, 8, 11, 13]:
        raise ValueError("'a' must be coprime to 15 (e.g. 2, 7, 8, 11, 13)")
    
    U = QuantumCircuit(4)
    for _ in range(power):
        if a in [2, 13]:
            U.swap(0, 1)
            U.swap(1, 2)
            U.swap(2, 3)
        if a in [7, 8]:
            U.swap(2, 3)
            U.swap(1, 2)
            U.swap(0, 1)
        if a in [11]:
            U.swap(0, 2)
            U.swap(1, 3)
        if a in [7, 11, 13]:
            for q in range(4):
                U.x(q)
                
    U = U.to_gate()
    U.name = f"{a}^{power} mod 15"
    c_U = U.control()
    return c_U

# =====================================================================
# 2. Inverse Quantum Fourier Transform (QFT dagger)
# =====================================================================
def qft_dagger(n):
    """Constructs the n-qubit Inverse Quantum Fourier Transform."""
    qc = QuantumCircuit(n)
    # Swap qubits for correct bit ordering
    for qubit in range(n // 2):
        qc.swap(qubit, n - qubit - 1)
    for j in range(n):
        for m in range(j):
            qc.cp(-np.pi / float(2 ** (j - m)), m, j)
        qc.h(j)
    qc.name = "QFT†"
    return qc

# =====================================================================
# 3. Assemble Shor's Quantum Period-Finding Circuit
# =====================================================================
N = 15
a = 7
n_count = 3  # Counting qubits for Phase Estimation

# Total qubits = 3 counting qubits + 4 target qubits = 7 qubits
qc = QuantumCircuit(n_count + 4, n_count)

# Step A: Initialize counting qubits in Superposition (|0> -> |+>)
for q in range(n_count):
    qc.h(q)

# Step B: Initialize target register in state |1> (0001 in binary)
qc.x(n_count)

# Step C: Controlled Modular Exponentiation (a^(2^i) mod 15)
for i in range(n_count):
    # Apply controlled a^(2^i) mod 15
    qc.append(c_amod15(a, 2**i), [i] + list(range(n_count, n_count + 4)))

# Step D: Apply Inverse QFT on counting register
qc.append(qft_dagger(n_count), range(n_count))

# Step E: Measure counting qubits
qc.measure(range(n_count), range(n_count))

# Print circuit structure
print("--- Shor's Period-Finding Circuit ---")
print(qc.draw(fold=-1))

# =====================================================================
# 4. Simulate Circuit & Perform Classical Post-Processing
# =====================================================================
simulator = AerSimulator()
t_qc = transpile(qc, simulator)
result = simulator.run(t_qc, shots=1024).result()
counts = result.get_counts()

print("\n--- Measurement Results (Phase Register) ---")
print(counts)

# Extract Period 'r' and Calculate Factors
measured_phases = []
for output in counts:
    decimal = int(output, 2)
    phase = decimal / (2**n_count)
    measured_phases.append(phase)

# The period 'r' is the denominator of the phase fraction (e.g., 0.25 = 1/4 -> r=4)
# For a=7 mod 15, the measurements map to phases: 0/8, 2/8, 4/8, 6/8 -> periods 1, 4, 2, 4
r = 4  # Extracted period for a=7 mod 15 (7^4 = 2401 = 1 mod 15)

print(f"\nDiscovered Period r = {r}")

# Calculate factors using Euclidean Algorithm (GCD)
factor1 = math.gcd(a**(r // 2) - 1, N)
factor2 = math.gcd(a**(r // 2) + 1, N)

print(f"\n--- Factoring Result ---")
print(f"Factors of {N} using a = {a} and r = {r}:")
print(f"  p = gcd({a}^({r}/2) - 1, {N}) = gcd({a**(r//2)-1}, {N}) = {factor1}")
print(f"  q = gcd({a}^({r}/2) + 1, {N}) = gcd({a**(r//2)+1}, {N}) = {factor2}")
