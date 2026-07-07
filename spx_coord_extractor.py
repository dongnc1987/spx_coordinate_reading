import base64
import re
import struct
import xml.etree.ElementTree as ET

import streamlit as st
import pandas as pd


def natural_sort_key(filename: str):
    parts = re.split(r"(\d+)", filename)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def extract_coordinates(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)

    rtrem_data = None
    for elem in root.iter("ClassInstance"):
        if elem.attrib.get("Name") == "RTREM":
            data_elem = elem.find("Data")
            if data_elem is not None and data_elem.text:
                rtrem_data = data_elem.text.strip()
            break

    if rtrem_data is None:
        return None

    blob = base64.b64decode(rtrem_data)

    x = struct.unpack_from("<d", blob, 121)[0]
    y = struct.unpack_from("<d", blob, 129)[0]
    z = struct.unpack_from("<d", blob, 137)[0]

    return {"X": x, "Y": y, "Z": z}


st.title("SPX Coordinate Extractor")
st.write("Upload one or more Bruker .spx spectrum files to extract their stage X/Y/Z coordinates.")

uploaded_files = st.file_uploader("Choose .spx file(s)", type=["spx"], accept_multiple_files=True)

if uploaded_files:
    uploaded_files = sorted(uploaded_files, key=lambda f: natural_sort_key(f.name))

    rows = []
    for file in uploaded_files:
        try:
            coords = extract_coordinates(file.read())
        except ET.ParseError as e:
            st.error(f"{file.name}: could not parse XML ({e})")
            continue

        if coords is None:
            st.warning(f"{file.name}: no RTREM coordinate block found")
            continue

        rows.append({"File": file.name, **coords})

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False)
        st.download_button("Download as CSV", data=csv, file_name="coordinates.csv", mime="text/csv")
