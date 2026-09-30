from qiskit_ibm_runtime import QiskitRuntimeService

# 1. Configuration
#JOB_ID = "daufu25vr3kc73emtr10"  # Replace with your actual Job ID string
JOB_ID = "daudjr5vr3kc73empubg"  # Replace with your actual Job ID string

# 2. Connect to IBM Quantum Service
print(f"Connecting to IBM Quantum and fetching Job: {JOB_ID}...")
service = QiskitRuntimeService(channel="ibm_quantum_platform", instance="auto")

# 3. Retrieve the Job
job = service.job(JOB_ID)
status = job.status()
print(f"Job Status: {status}")

if status == "DONE":
    result = job.result()
    pub_result = result[0]

    # Extract classical bit counts dynamically
    data_bin = pub_result.data
    reg_name = list(data_bin.keys())[0]
    counts = getattr(data_bin, reg_name).get_counts()

    print("\n--- Raw QPU Measurement Counts ---")
    print(counts)

    # Calculate total shots and unique bitstrings observed
    total_shots = sum(counts.values())
    unique_outcomes = len(counts)
    
    print(f"\n--- Statistical Summary ---")
    print(f"Total Shots: {total_shots}")
    print(f"Unique Bitstring Outcomes Observed: {unique_outcomes}")
    print(f"Top 5 Most Frequent Outcomes: {sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]}")

else:
    print(f"Job is not completed yet. Current status: {status}")
