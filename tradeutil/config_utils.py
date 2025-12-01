import os

def _read_env_file(filepath):
    try:
        # Resolve filepath relative to project root (assuming this file is in tradeutil/config_utils.py)
        # However, .env is usually in the execution root. Let's try to look in the parent directory of tradeutil
        # if the filepath is not absolute.
        if not os.path.isabs(filepath):
            # Attempt to find it relative to CWD first (standard behavior)
            if not os.path.exists(filepath):
                # Try relative to the package location
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                alt_path = os.path.join(base_dir, filepath)
                if os.path.exists(alt_path):
                    filepath = alt_path

        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Handle "export KEY=VALUE"
                if line.startswith("export "):
                    line = line[7:].strip()

                if line.startswith("OLLAMA_HOST"):
                    # Split by first '='
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key == "OLLAMA_HOST":
                            value = parts[1].strip()

                            # Handle inline comments (basic: assume # preceded by space is comment, or just # if it's a simple parser)
                            # To be safer for URLs, we only split if " #" is present, or if we want to be standard compliant, # anywhere.
                            # But since standard dotenv allows # for comments, we stick to it but maybe check for space.
                            # However, URLs rarely have # unless fragments. Let's assume standard behavior: # starts comment.
                            if " #" in value:
                                value = value.split(" #", 1)[0].strip()
                            elif value.startswith("#"): # Should have been caught by line start check but if value starts with #
                                value = ""

                            # Strip quotes if present
                            if (value.startswith('"') and value.endswith('"')) or \
                               (value.startswith("'") and value.endswith("'")):
                                value = value[1:-1]
                            return value
    except Exception:
        pass
    return None

def get_ollama_host():
    """
    Resolves OLLAMA_HOST in the following order:
    1. Environment variable OLLAMA_HOST
    2. .env file
    3. .env.template file
    4. Default (http://localhost:11435)
    """
    # 1. Check environment variable
    host = os.environ.get("OLLAMA_HOST")
    if host:
        return host

    # 2. Check .env
    host = _read_env_file(".env")
    if host:
        return host

    # 3. Check .env.template
    host = _read_env_file(".env.template")
    if host:
        return host

    # 4. Default
    return "http://localhost:11435"
