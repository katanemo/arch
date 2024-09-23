from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/agent/device_reboot', methods=['POST'])
def reboot_devices():
    """
    Endpoint to reboot devices based on device IDs or a device group.
    """
    data = request.get_json()

    # Extract parameters based on the prompt targets definition
    device_ids = data.get('device_ids')
    device_group = data.get('device_group')

    # Validate that at least one parameter is provided
    if not device_ids and not device_group:
        return jsonify({'error': "At least one of 'device_ids' or 'device_group' must be provided."}), 400

    devices_to_reboot = []

    # Process 'device_ids' if provided
    if device_ids:
        if not isinstance(device_ids, list):
            return jsonify({'error': "'device_ids' must be a list."}), 400
        devices_to_reboot.extend(device_ids)

    # Process 'device_group' if provided
    if device_group:
        if not isinstance(device_group, str):
            return jsonify({'error': "'device_group' must be a string."}), 400
        # Simulate retrieving device IDs from the device group
        # In a real application, replace this with actual data retrieval
        group_devices = get_devices_by_group(device_group)
        if not group_devices:
            return jsonify({'error': f"No devices found in group '{device_group}'."}), 404
        devices_to_reboot.extend(group_devices)

    # Remove duplicates in case of overlap between device_ids and device_group
    devices_to_reboot = list(set(devices_to_reboot))

    # Simulate rebooting devices
    reboot_results = []
    for device_id in devices_to_reboot:
        # Placeholder for actual reboot logic
        result = {
            'device_id': device_id,
            'status': 'Reboot initiated'
        }
        reboot_results.append(result)

    response = {
        'reboot_results': reboot_results
    }

    return jsonify(response), 200

def get_devices_by_group(group_name):
    """
    Simulate retrieving device IDs based on a device group name.
    In a real application, this would query a database or external service.
    """
    # Placeholder data for demonstration purposes
    device_groups = {
        'Sales': ['1001', '1002', '1003'],
        'Engineering': ['2001', '2002', '2003'],
        'Data Center': ['3001', '3002', '3003']
    }
    return device_groups.get(group_name, [])

if __name__ == '__main__':
    app.run(debug=True)
