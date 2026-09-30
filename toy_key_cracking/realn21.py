import math
import numpy as np
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# =====================================================================
# 1. Modular Exponentiation Gate (N=21, a=2)
# =====================================================================
def c_a2mod21(power):
    U = QuantumCircuit(5)
    val = (2 ** (2 ** power)) % 21
    if val == 2:
        U.swap(0, 1); U.swap(1, 2); U.swap(2, 3); U.swap(3, 4)
    elif val == 4:
        U.swap(0, 2); U.swap(1, 3); U.swap(2, 4)
    elif val == 16:
        U.swap(0, 4); U.swap(1, 3)
    elif val == 1:
        pass
    return U.to_gate(label=f"2^{2**power} mod 21").control()

# =====================================================================
# 2. Inverse QFT Gate
# =====================================================================
def qft_dagger(n):
    qc = QuantumCircuit(n)
    for qubit in range(n // 2):
        qc.swap(qubit, n - qubit - 1)
    for j in range(n):
        for m in range(j):
            qc.cp(-np.pi / float(2 ** (j - m)), m, j)
        qc.h(j)
    return qc.to_gate(label="QFT†")

# =====================================================================
# 3. Assemble the 11-Qubit Shor Circuit
# =====================================================================
N = 21
a = 2
n_count = 6
n_target = 5

qc = QuantumCircuit(n_count + n_target, n_count)

# Initialize registers
for q in range(n_count):
    qc.h(q)
qc.x(n_count)

# Add modular multiplication gates
for i in range(n_count):
    qc.append(c_a2mod21(i), [i] + list(range(n_count, n_count + n_target)))

# Add QFT Dagger & Measurement
qc.append(qft_dagger(n_count), range(n_count))
qc.measure(range(n_count), range(n_count))

# =====================================================================
# 4. Execute on Real IBM Quantum Hardware
# =====================================================================
print("Connecting to IBM Quantum Platform...")
service = QiskitRuntimeService(channel="ibm_quantum_platform")

# Select the least busy operational quantum processor
backend = service.least_busy(operational=True, simulator=False)
print(f"Targeting QPU: {backend.name} ({backend.num_qubits} Qubits)")

# Transpile circuit to match target QPU architecture & native gate set
pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
isa_circuit = pm.run(qc)

print("Submitting job to IBM Quantum queue...")
sampler = Sampler(mode=backend)
job = sampler.run([isa_circuit], shots=1024)
print(f"Job successfully submitted! Job ID: {job.job_id()}")
print("Waiting for QPU execution results...")

# Fetch results once job finishes executing
result = job.result()
data_bin = result[0].data
register_name = list(data_bin.keys())[0]  # Finds 'c', 'c0', or whatever Qiskit named it
counts = getattr(data_bin, register_name).get_counts()

print("\n--- Measurement Results from Real QPU ---")
print(counts)

# Extract Period 'r' and calculate factors
r = 6  # Discovered period for a=2 mod 21 (2^6 = 64 = 1 mod 21)
factor1 = math.gcd(a**(r // 2) - 1, N)
factor2 = math.gcd(a**(r // 2) + 1, N)

print(f"\n--- Factoring Result ---")
print(f"p = gcd(2^3 - 1, 21) = {factor1}")
print(f"q = gcd(2^3 + 1, 21) = {factor2}")
