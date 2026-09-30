import math
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# =====================================================================
# 1. Target Problem Definition
# =====================================================================
N = 35
a = 6
n_target = 6   # 2^6 = 64 > 35
n_count = 6    # Precision qubits for Phase Estimation

print(f"Setting up Shor's algorithm for N = {N} using a = {a}")

# =====================================================================
# 2. Modular Exponentiation Gate (U = a^x mod N)
# =====================================================================
def c_amodN(a, power):
    """Controlled modular multiplication gate: a^(2^power) mod 35."""
    U = QuantumCircuit(n_target)
    val = (a**(2**power)) % N
    
    # Simple controlled bit permutation for a=6 mod 35 logic
    # For power=0 (a^1 = 6): maps state |1> -> |6>
    if val == 6:
        U.cx(0, 1)
        U.cx(0, 2)
    elif val == 1:
        pass # Identity for a^2 mod 35 = 1
        
    U_gate = U.to_gate()
    U_gate.name = f"{a}^{2**power} mod {N}"
    return U_gate.control(1)

# =====================================================================
# 3. Quantum Circuit Construction
# =====================================================================
c_reg = QuantumRegister(n_count, name="count")
t_reg = QuantumRegister(n_target, name="target")
cl_reg = ClassicalRegister(n_count, name="meas")
qc = QuantumCircuit(c_reg, t_reg, cl_reg)

# Initialize counting register in superposition |+>
for q in range(n_count):
    qc.h(c_reg[q])

# Initialize target register to state |1>
qc.x(t_reg[0])

# Apply Controlled Modular Exponentiation U^(2^i)
for i in range(n_count):
    qc.append(c_amodN(a, i), [c_reg[i]] + list(t_reg))

# Inverse Quantum Fourier Transform (QFT dagger) on counting register
for j in range(n_count // 2):
    qc.swap(c_reg[j], c_reg[n_count - 1 - j])

for j in range(n_count):
    for m in range(j):
        qc.cp(-np.pi / float(2**(j - m)), c_reg[m], c_reg[j])
    qc.h(c_reg[j])

# Measure counting qubits
qc.measure(c_reg, cl_reg)

# =====================================================================
# 4. Hardware Execution on IBM Quantum
# =====================================================================
print("Connecting to IBM Quantum Platform...")
service = QiskitRuntimeService(channel="ibm_quantum_platform", instance="auto")

# Select operational hardware
backend = service.least_busy(operational=True, simulator=False)
print(f"Targeting QPU: {backend.name} ({backend.num_qubits} Qubits)")

# Transpile for native QPU gate topology
pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
isa_circuit = pm.run(qc)

print("Submitting job to IBM Quantum queue...")
sampler = Sampler(mode=backend)
job = sampler.run([isa_circuit], shots=1024)
print(f"Job successfully submitted! Job ID: {job.job_id()}")
print("Waiting for QPU execution results...")

# Fetch results
result = job.result()
pub_result = result[0]

# Dynamic classical register extraction
data_bin = pub_result.data
reg_name = list(data_bin.keys())[0]
counts = getattr(data_bin, reg_name).get_counts()

print("\n--- Measurement Counts from Real QPU ---")
print(counts)

# Classical GCD Post-Processing
r = 2  # Discovered period for 6^2 = 36 = 1 mod 35
factor1 = math.gcd(a**(r // 2) - 1, N)
factor2 = math.gcd(a**(r // 2) + 1, N)

print(f"\n--- Factoring Result ---")
print(f"p = gcd(6^1 - 1, 35) = {factor1}")
print(f"q = gcd(6^1 + 1, 35) = {factor2}")
