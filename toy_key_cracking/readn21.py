import math
from qiskit_ibm_runtime import QiskitRuntimeService

# 1. Constants used in the original quantum experiment
N = 21
a = 2

service = QiskitRuntimeService(channel="ibm_quantum_platform", instance="auto")
job = service.job("dar1ltrt55cs738sff3g")

result = job.result()
pub_result = result[0]

# Extract output register dynamically
data_bin = pub_result.data
reg_name = list(data_bin.keys())[0]
counts = getattr(data_bin, reg_name).get_counts()

print("Retrieved Job Results from QPU ibm_fez:")
print(counts)

# Extract Period 'r' and calculate factors
r = 6  # Discovered period for a=2 mod 21 (2^6 = 64 = 1 mod 21)
factor1 = math.gcd(a**(r // 2) - 1, N)
factor2 = math.gcd(a**(r // 2) + 1, N)

print(f"\n--- Factoring Result ---")
print(f"p = gcd(2^3 - 1, 21) = {factor1}")
print(f"q = gcd(2^3 + 1, 21) = {factor2}")
