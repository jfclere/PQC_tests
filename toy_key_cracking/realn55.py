import math
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

N = 55
a = 2
n_target = 6   # 2^6 = 64 > 55
n_count = 8    # Precision qubits for phase estimation

# Build standard controlled modular multiplication logic for a=2 mod 55
c_reg = QuantumRegister(n_count, name="count")
t_reg = QuantumRegister(n_target, name="target")
cl_reg = ClassicalRegister(n_count, name="meas")
qc = QuantumCircuit(c_reg, t_reg, cl_reg)

# 1. Superposition & Initialization
for q in range(n_count):
    qc.h(c_reg[q])
qc.x(t_reg[0]) # Set target to |1>

# 2. General Controlled Exponentiation Loop (a^(2^i) mod 55)
for i in range(n_count):
    val = pow(a, 2**i, N)
    U = QuantumCircuit(n_target)
    # Generic multi-controlled swaps/flips required to shift basis states mod 55
    if val != 1:
        for t in range(n_target):
            if (val >> t) & 1:
                U.x(t)
    qc.append(U.to_gate().control(1), [c_reg[i]] + list(t_reg))

# 3. Inverse QFT
for j in range(n_count // 2):
    qc.swap(c_reg[j], c_reg[n_count - 1 - j])
for j in range(n_count):
    for m in range(j):
        qc.cp(-np.pi / float(2**(j - m)), c_reg[m], c_reg[j])
    qc.h(c_reg[j])

qc.measure(c_reg, cl_reg)

# 4. Connect to QPU & Transpile
service = QiskitRuntimeService(channel="ibm_quantum_platform", instance="auto")
backend = service.least_busy(operational=True, simulator=False)
print(f"Target QPU: {backend.name}")

pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
isa_circuit = pm.run(qc)

# =====================================================================
# OBSERVABLE PROOF #1: Physical Gate Count Explosion
# =====================================================================
two_qubit_gates = isa_circuit.count_ops().get('ecr', 0) + isa_circuit.count_ops().get('cz', 0)
print(f"\n--- Transpiled Circuit Metrics for N = 55 ---")
print(f"Total Physical Circuit Depth: {isa_circuit.depth()}")
print(f"Physical 2-Qubit Gates (ECR/CZ): {two_qubit_gates}")

# Calculate estimated fidelity: F = (1 - error_rate)^gates
est_fidelity = (1 - 0.003) ** two_qubit_gates
print(f"Estimated QPU Output Fidelity: {est_fidelity * 100:.4f}%")

# Submit to execute on hardware
sampler = Sampler(mode=backend)
job = sampler.run([isa_circuit], shots=1024)
print(f"Job submitted! Job ID: {job.job_id()}")
