## Setup Instructions(User): archgw CLI

This guide will walk you through the steps to set up the archgw cli on your local machine

### Step 1: Create a Python virtual environment

In the tools directory, create a Python virtual environment by running:

```bash
python -m venv venv
```

### Step 2: Activate the virtual environment
* On Linux/MacOS:

```bash
source venv/bin/activate
```

### Step 3: Run the build script
```bash
pip install archgw
```

## Uninstall Instructions: archgw CLI
```bash
pip uninstall archgw
```

## Setup Instructions (Dev): archgw CLI

This guide will walk you through the steps to set up the archgw cli on your local machine when you want to develop the Archgw CLI

### Step 1: Create a Python virtual environment

In the tools directory, create a Python virtual environment by running:

```bash
python -m venv venv
```

### Step 2: Activate the virtual environment
* On Linux/MacOS:

```bash
source venv/bin/activate
```

### Step 3: Run the build script
```bash
sh build_cli.sh
```

### Step 4: build Arch
```bash
archgw build
```

### Step 5: download models
This will help download models so model_server can load faster. This should be done once.

```bash
archgw download-models
```

### Logs
`archgw` command can also view logs from gateway and model_server. Use following command to view logs,

```bash
archgw logs --follow
```

## Uninstall Instructions: archgw CLI
```bash
pip uninstall archgw
