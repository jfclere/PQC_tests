from qiskit_ibm_runtime import QiskitRuntimeService
import os

# Save API token locally to ~/.qiskit/qiskit-ibm.json
QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform",
    token=os.getenv("QISKIT_IBM_TOKEN"),
    overwrite=True
)
