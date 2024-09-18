import pandas as pd
import random
from datetime import datetime, timedelta, timezone

# Function to generate random MAC addresses
def random_mac():
    return "AA:BB:CC:DD:EE:" + ':'.join([f"{random.randint(0, 255):02X}" for _ in range(2)])

# Function to generate random IP addresses
def random_ip():
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

# Generate synthetic data for the device table
def generate_device_data(conn, n=1000,):
    device_data = {
        'switchip': [random_ip() for _ in range(n)],
        'hwsku': [f'HW{i+1}' for i in range(n)],
        'hostname': [f'switch{i+1}' for i in range(n)],
        'osversion': [f'v{i+1}' for i in range(n)],
        'layer': ['L2' if i % 2 == 0 else 'L3' for i in range(n)],
        'region': [random.choice(['US', 'EU', 'ASIA']) for _ in range(n)],
        'uptime': [f'{random.randint(0, 10)} days {random.randint(0, 23)}:{random.randint(0, 59)}:{random.randint(0, 59)}' for _ in range(n)],
        'device_mac_address': [random_mac() for _ in range(n)]
    }
    df = pd.DataFrame(device_data)
    df.to_sql('device', conn, index=False)
    return df

# Generate synthetic data for the interfacestats table
def generate_interface_stats_data(conn, device_df, n=1000):
    interface_stats_data = []
    for _ in range(n):
        device_mac = random.choice(device_df['device_mac_address'])
        ifname = random.choice(['eth0', 'eth1', 'eth2', 'eth3'])
        time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 1440))  # random timestamps in the past day
        in_discards = random.randint(0, 1000)
        in_errors = random.randint(0, 500)
        out_discards = random.randint(0, 800)
        out_errors = random.randint(0, 400)
        in_octets = random.randint(1000, 100000)
        out_octets = random.randint(1000, 100000)

        interface_stats_data.append({
            'device_mac_address': device_mac,
            'ifname': ifname,
            'time': time,
            'in_discards': in_discards,
            'in_errors': in_errors,
            'out_discards': out_discards,
            'out_errors': out_errors,
            'in_octets': in_octets,
            'out_octets': out_octets
        })
    df = pd.DataFrame(interface_stats_data)
    df.to_sql('interfacestats', conn, index=False)
    return 

# Generate synthetic data for the ts_flow table
def generate_flow_data(conn, device_df, n=1000):
    flow_data = []
    for _ in range(n):
        sampler_address = random.choice(device_df['switchip'])
        proto = random.choice(['TCP', 'UDP'])
        src_addr = random_ip()
        dst_addr = random_ip()
        src_port = random.randint(1024, 65535)
        dst_port = random.randint(1024, 65535)
        in_if = random.randint(1, 10)
        out_if = random.randint(1, 10)
        flow_start = int((datetime.now() - timedelta(days=random.randint(1, 30))).timestamp())
        flow_end = int((datetime.now() - timedelta(days=random.randint(1, 30))).timestamp())
        bytes_transferred = random.randint(1000, 100000)
        packets = random.randint(1, 1000)
        flow_time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 1440))  # random flow time

        flow_data.append({
            'sampler_address': sampler_address,
            'proto': proto,
            'src_addr': src_addr,
            'dst_addr': dst_addr,
            'src_port': src_port,
            'dst_port': dst_port,
            'in_if': in_if,
            'out_if': out_if,
            'flow_start': flow_start,
            'flow_end': flow_end,
            'bytes': bytes_transferred,
            'packets': packets,
            'time': flow_time
        })
    df = pd.DataFrame(flow_data)
    df.to_sql('ts_flow', conn, index=False)
    return 