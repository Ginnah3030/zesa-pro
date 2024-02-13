import secrets

# Generate a secure random hex string (16 bytes)
secret_key = secrets.token_hex(16)

print(secret_key)
