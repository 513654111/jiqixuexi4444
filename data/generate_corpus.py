import os, random
CORPUS_DIR = "data/corpus"
os.makedirs(CORPUS_DIR, exist_ok=True)
policies = [
    "Remote work policy: 3 days per week allowed.",
    "PTO: 15 days per year, request 2 weeks in advance.",
    "VPN setup: Use company client + RSA token.",
    "Expense limit: $500 monthly without approval.",
    "Security: Never share passwords, use password manager.",
]
for i in range(30):
    topic = random.choice(policies)
    with open(os.path.join(CORPUS_DIR, f"doc_{i:03d}.txt"), "w") as f:
        f.write(f"{topic} Additional details for doc {i}.")
print(f"Generated 30 documents in {CORPUS_DIR}")
