import pandas as pd
import random
from datetime import datetime, timedelta, timezone
import re
import logging
from dateparser import parse
import sqlite3

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_sql():
    # Example Usage
    conn = sqlite3.connect(":memory:")

    # create and load the devices table
    device_data = generate_device_data(conn)

    # create and load the interface_stats table
    generate_interface_stats_data(conn, device_data)

    # create and load the flow table
    generate_flow_data(conn, device_data)

    return conn


# Function to convert natural language time expressions to "X {time} ago" format
def convert_to_ago_format(expression):
    # Define patterns for different time units
    time_units = {
        r"seconds": "seconds",
        r"minutes": "minutes",
        r"mins": "mins",
        r"hrs": "hrs",
        r"hours": "hours",
        r"hour": "hour",
        r"hr": "hour",
        r"days": "days",
        r"day": "day",
        r"weeks": "weeks",
        r"week": "week",
        r"months": "months",
        r"month": "month",
        r"years": "years",
        r"yrs": "years",
        r"year": "year",
        r"yr": "year",
    }

    # Iterate over each time unit and create regex for each phrase format
    for pattern, unit in time_units.items():
        # Handle "for the past X {unit}"
        match = re.search(rf"(\d+) {pattern}", expression)
        if match:
            quantity = match.group(1)
            return f"{quantity} {unit} ago"

    # If the format is not recognized, return None or raise an error
    return None


# Function to generate random MAC addresses
def random_mac():
    return "AA:BB:CC:DD:EE:" + ":".join(
        [f"{random.randint(0, 255):02X}" for _ in range(2)]
    )


# Function to generate random IP addresses
def random_ip():
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"


# Generate synthetic data for the device table
def generate_device_data(
    conn,
    n=1000,
):
    device_data = {
        "switchip": [random_ip() for _ in range(n)],
        "hwsku": [f"HW{i+1}" for i in range(n)],
        "hostname": [f"switch{i+1}" for i in range(n)],
        "osversion": [f"v{i+1}" for i in range(n)],
        "layer": ["L2" if i % 2 == 0 else "L3" for i in range(n)],
        "region": [random.choice(["US", "EU", "ASIA"]) for _ in range(n)],
        "uptime": [
            f"{random.randint(0, 10)} days {random.randint(0, 23)}:{random.randint(0, 59)}:{random.randint(0, 59)}"
            for _ in range(n)
        ],
        "device_mac_address": [random_mac() for _ in range(n)],
    }
    df = pd.DataFrame(device_data)
    df.to_sql("device", conn, index=False)
    return df


# Generate synthetic data for the interfacestats table
def generate_interface_stats_data(conn, device_df, n=1000):
    interface_stats_data = []
    for _ in range(n):
        device_mac = random.choice(device_df["device_mac_address"])
        ifname = random.choice(["eth0", "eth1", "eth2", "eth3"])
        time = datetime.now(timezone.utc) - timedelta(
            minutes=random.randint(0, 1440 * 5)
        )  # random timestamps in the past 5 day
        in_discards = random.randint(0, 1000)
        in_errors = random.randint(0, 500)
        out_discards = random.randint(0, 800)
        out_errors = random.randint(0, 400)
        in_octets = random.randint(1000, 100000)
        out_octets = random.randint(1000, 100000)

        interface_stats_data.append(
            {
                "device_mac_address": device_mac,
                "ifname": ifname,
                "time": time,
                "in_discards": in_discards,
                "in_errors": in_errors,
                "out_discards": out_discards,
                "out_errors": out_errors,
                "in_octets": in_octets,
                "out_octets": out_octets,
            }
        )
    df = pd.DataFrame(interface_stats_data)
    df.to_sql("interfacestats", conn, index=False)
    return


# Generate synthetic data for the ts_flow table
def generate_flow_data(conn, device_df, n=1000):
    flow_data = []
    for _ in range(n):
        sampler_address = random.choice(device_df["switchip"])
        proto = random.choice(["TCP", "UDP"])
        src_addr = random_ip()
        dst_addr = random_ip()
        src_port = random.randint(1024, 65535)
        dst_port = random.randint(1024, 65535)
        in_if = random.randint(1, 10)
        out_if = random.randint(1, 10)
        flow_start = int(
            (datetime.now() - timedelta(days=random.randint(1, 30))).timestamp()
        )
        flow_end = int(
            (datetime.now() - timedelta(days=random.randint(1, 30))).timestamp()
        )
        bytes_transferred = random.randint(1000, 100000)
        packets = random.randint(1, 1000)
        flow_time = datetime.now(timezone.utc) - timedelta(
            minutes=random.randint(0, 1440 * 5)
        )  # random flow time

        flow_data.append(
            {
                "sampler_address": sampler_address,
                "proto": proto,
                "src_addr": src_addr,
                "dst_addr": dst_addr,
                "src_port": src_port,
                "dst_port": dst_port,
                "in_if": in_if,
                "out_if": out_if,
                "flow_start": flow_start,
                "flow_end": flow_end,
                "bytes": bytes_transferred,
                "packets": packets,
                "time": flow_time,
            }
        )
    df = pd.DataFrame(flow_data)
    df.to_sql("ts_flow", conn, index=False)
    return


def load_params(req):
    # Step 1: Convert the from_time natural language string to a timestamp if provided
    if req.from_time:
        # Use `dateparser` to parse natural language timeframes
        logger.info(f"{'* ' * 50}\n\nCaptured from time: {req.from_time}\n\n")
        parsed_time = parse(req.from_time, settings={"RELATIVE_BASE": datetime.now()})
        if not parsed_time:
            conv_time = convert_to_ago_format(req.from_time)
            if conv_time:
                parsed_time = parse(
                    conv_time, settings={"RELATIVE_BASE": datetime.now()}
                )
            else:
                return {
                    "error": "Invalid from_time format. Please provide a valid time description such as 'past 7 days' or 'since last month'."
                }
        logger.info(f"\n\nConverted from time: {parsed_time}\n\n{'* ' * 50}\n\n")
        from_time = parsed_time
        logger.info(f"Using parsed from_time: {from_time}")
    else:
        # If no from_time is provided, use a default value (e.g., the past 7 days)
        from_time = datetime.now() - timedelta(days=7)
        logger.info(f"Using default from_time: {from_time}")

    # Step 2: Build the dynamic SQL query based on the optional filters
    filters = []
    params = {"from_time": from_time}

    if req.ifname:
        filters.append("i.ifname = :ifname")
        params["ifname"] = req.ifname

    if req.region:
        filters.append("d.region = :region")
        params["region"] = req.region

    if req.min_in_errors is not None:
        filters.append("i.in_errors >= :min_in_errors")
        params["min_in_errors"] = req.min_in_errors

    if req.max_in_errors is not None:
        filters.append("i.in_errors <= :max_in_errors")
        params["max_in_errors"] = req.max_in_errors

    if req.min_out_errors is not None:
        filters.append("i.out_errors >= :min_out_errors")
        params["min_out_errors"] = req.min_out_errors

    if req.max_out_errors is not None:
        filters.append("i.out_errors <= :max_out_errors")
        params["max_out_errors"] = req.max_out_errors

    if req.min_in_discards is not None:
        filters.append("i.in_discards >= :min_in_discards")
        params["min_in_discards"] = req.min_in_discards

    if req.max_in_discards is not None:
        filters.append("i.in_discards <= :max_in_discards")
        params["max_in_discards"] = req.max_in_discards

    if req.min_out_discards is not None:
        filters.append("i.out_discards >= :min_out_discards")
        params["min_out_discards"] = req.min_out_discards

    if req.max_out_discards is not None:
        filters.append("i.out_discards <= :max_out_discards")
        params["max_out_discards"] = req.max_out_discards

    return params, filters
