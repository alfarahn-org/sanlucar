 #!/bin/sh

echo ""
echo "Loading azd .env file from current environment"
echo ""

while IFS='=' read -r key value; do
    value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
    export "$key=$value"
done <<EOF
$(azd env get-values)
EOF

echo 'Creating python virtual environment "scripts/.venv"'
python3 -m venv evaluation/.venv

echo 'Installing dependencies from "requirements.txt" into virtual environment'
./evaluation/.venv/bin/python -m pip install -r evaluation/requirements.txt

echo 'Running "prepdocs.py"'
python3 ./evaluation/evaluator.py
