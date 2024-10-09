from fastapi import FastAPI, Response
from datetime import datetime, timezone
import logging
from pydantic import BaseModel
from utils import load_sql, load_params
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok"
    }

conn = load_sql()
name_col = "name"


class PacketDropCorrelationRequest(BaseModel):
    from_time: str = None  # Optional natural language timeframe
    ifname: str = None  # Optional interface name filter
    region: str = None  # Optional region filter
    min_in_errors: int = None
    max_in_errors: int = None
    min_out_errors: int = None
    max_out_errors: int = None
    min_in_discards: int = None
    max_in_discards: int = None
    min_out_discards: int = None
    max_out_discards: int = None


@app.post("/interface_down_pkt_drop")
async def interface_down_packet_drop(req: PacketDropCorrelationRequest, res: Response):
    params, filters = load_params(req)

    # Join the filters using AND
    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "AND " + where_clause

    # Step 3: Query packet errors and flows from interfacestats and ts_flow
    query = f"""
    SELECT
      d.switchip AS device_ip_address,
      i.in_errors,
      i.in_discards,
      i.out_errors,
      i.out_discards,
      i.ifname,
      t.src_addr,
      t.dst_addr,
      t.time AS flow_time,
      i.time AS interface_time
    FROM
      device d
    INNER JOIN
      interfacestats i
      ON d.device_mac_address = i.device_mac_address
    INNER JOIN
      ts_flow t
      ON d.switchip = t.sampler_address
    WHERE
      i.time >= :from_time  -- Using the converted timestamp
      {where_clause}
    ORDER BY
      i.time;
    """

    correlated_data = pd.read_sql_query(query, conn, params=params)

    if correlated_data.empty:
        default_response = {
            "device_ip_address": "0.0.0.0",  # Placeholder IP
            "in_errors": 0,
            "in_discards": 0,
            "out_errors": 0,
            "out_discards": 0,
            "ifname": req.ifname
            or "unknown",  # Placeholder or interface provided in the request
            "src_addr": "0.0.0.0",  # Placeholder source IP
            "dst_addr": "0.0.0.0",  # Placeholder destination IP
            "flow_time": str(
                datetime.now(timezone.utc)
            ),  # Current timestamp or placeholder
            "interface_time": str(
                datetime.now(timezone.utc)
            ),  # Current timestamp or placeholder
        }
        return [default_response]

    logger.info(f"Correlated Packet Drop Data: {correlated_data}")

    return correlated_data.to_dict(orient='records')


class FlowPacketErrorCorrelationRequest(BaseModel):
    from_time: str = None  # Optional natural language timeframe
    ifname: str = None  # Optional interface name filter
    region: str = None  # Optional region filter
    min_in_errors: int = None
    max_in_errors: int = None
    min_out_errors: int = None
    max_out_errors: int = None
    min_in_discards: int = None
    max_in_discards: int = None
    min_out_discards: int = None
    max_out_discards: int = None


@app.post("/packet_errors_impact_flow")
async def packet_errors_impact_flow(
    req: FlowPacketErrorCorrelationRequest, res: Response
):
    params, filters = load_params(req)

    # Join the filters using AND
    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "AND " + where_clause

    # Step 3: Query the packet errors and flows, correlating by timestamps
    query = f"""
    SELECT
      d.switchip AS device_ip_address,
      i.in_errors,
      i.in_discards,
      i.out_errors,
      i.out_discards,
      i.ifname,
      t.src_addr,
      t.dst_addr,
      t.src_port,
      t.dst_port,
      t.packets,
      t.time AS flow_time,
      i.time AS error_time
    FROM
      device d
    INNER JOIN
      interfacestats i
      ON d.device_mac_address = i.device_mac_address
    INNER JOIN
      ts_flow t
      ON d.switchip = t.sampler_address
    WHERE
      i.time >= :from_time
      AND ABS(strftime('%s', t.time) - strftime('%s', i.time)) <= 300  -- Correlate within 5 minutes
      {where_clause}
    ORDER BY
      i.time;
    """

    correlated_data = pd.read_sql_query(query, conn, params=params)

    if correlated_data.empty:
        default_response = {
            "device_ip_address": "0.0.0.0",  # Placeholder IP
            "in_errors": 0,
            "in_discards": 0,
            "out_errors": 0,
            "out_discards": 0,
            "ifname": req.ifname
            or "unknown",  # Placeholder or interface provided in the request
            "src_addr": "0.0.0.0",  # Placeholder source IP
            "dst_addr": "0.0.0.0",  # Placeholder destination IP
            "src_port": 0,
            "dst_port": 0,
            "packets": 0,
            "flow_time": str(
                datetime.now(timezone.utc)
            ),  # Current timestamp or placeholder
            "error_time": str(
                datetime.now(timezone.utc)
            ),  # Current timestamp or placeholder
        }
        return [default_response]

    # Return the correlated data if found
    return correlated_data.to_dict(orient='records')
