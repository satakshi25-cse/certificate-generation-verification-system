import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import qrcode
import os
import zipfile
import tempfile
from io import BytesIO
import uuid

#Get certificate id from qr code url
query_params=st.query_params
qr_certificate_id=query_params.get("certificate_id")

st.set_page_config(page_title="Certificate Generation & Verification System")
st.title("Certificate Generation & Verification System")

# File where valid certificate records are stored
RECORD_FILE = "certificates.csv"

# Create two tabs
generate_tab, verify_tab = st.tabs(["Generate Certificates", "Verify Certificate"])

# GENERATE CERTIFICATES TAB

with generate_tab:
    st.header("Generate Certificates")
    st.write(
        "Upload a certificate template and an Excel file "
        "to automatically generate certificates."
    )
    template_file = st.file_uploader("Upload Certificate Template",type=["png", "jpg", "jpeg"])
    excel_file = st.file_uploader("Upload Participant Excel File",type=["xlsx"])
    font_size = st.number_input("Enter Name Font Size",min_value=20,max_value=200,value=150)

    if template_file and excel_file:
        df = pd.read_excel(excel_file)
        st.subheader("Participant Data")
        st.dataframe(df)
        if "Name" not in df.columns:
            st.error("Excel file must contain a column named 'Name'")
        else:
            if st.button("Generate Certificates"):
                temp_dir = tempfile.mkdtemp()
                output_folder = os.path.join(temp_dir,"certificates")
                os.makedirs( output_folder,exist_ok=True)
                template = Image.open(template_file)
                try:
                    font = ImageFont.truetype("arial.ttf",font_size)
                except:
                    font = ImageFont.load_default()
                progress_bar = st.progress(0)

                # Stores newly generated certificate data
                certificate_records = []
                for index, row in df.iterrows():
                    name = str(row["Name"])

                    # Generate unique certificate ID
                    certificate_id = ("CERT-"+ uuid.uuid4().hex[:8].upper())
                    certificate = template.copy()
                    draw = ImageDraw.Draw(certificate)

                    # Calculate name size
                    bbox = draw.textbbox((0, 0),name,font=font)
                    text_width = bbox[2] - bbox[0]

                    # Center name
                    name_x = (certificate.width - text_width) / 2
                    name_y = certificate.height / 2

                    # Draw participant name
                    draw.text((name_x, name_y),name,font=font,fill="black")

                    # QR Code Data
                    verification_url=f"https://satakshi25-cse-certificate-generation-verification-s-app-sfostp.streamlit.app/?certificate_id={certificate_id}"
                    qr_data = verification_url
                    qr = qrcode.make(qr_data)
                    qr = qr.resize((100, 100))
                    margin = 80
                    qr_x = (certificate.width- qr.width- margin)
                    qr_y = (certificate.height- qr.height- margin)
                    certificate.paste(qr,(qr_x, qr_y))
                    safe_name = name.replace(" ", "_")
                    filename = (f"{safe_name}_{certificate_id}.png")
                    certificate.save(os.path.join(output_folder,filename))

                    # Store certificate details
                    certificate_records.append(
                        {
                            "Certificate_ID": certificate_id,
                            "Name": name
                        }
                    )
                    progress_bar.progress((index + 1) / len(df))

                # Convert new records to DataFrame
                new_records_df = pd.DataFrame(certificate_records)

                # If certificates.csv already exists
                if os.path.exists(RECORD_FILE):
                    old_records_df = pd.read_csv(RECORD_FILE)
                    updated_records_df = pd.concat(
                        [
                            old_records_df,
                            new_records_df
                        ],
                        ignore_index=True
                    )
                else:
                    updated_records_df = new_records_df

                # Save all certificate records
                updated_records_df.to_csv(RECORD_FILE,index=False)

                # Create ZIP file
                zip_buffer = BytesIO()
                with zipfile.ZipFile(
                    zip_buffer,
                    "w",
                    zipfile.ZIP_DEFLATED
                ) as zip_file:
                    for filename in os.listdir(output_folder):
                        file_path = os.path.join(output_folder,filename)
                        zip_file.write(file_path,filename)
                st.success(f"{len(df)} certificates generated successfully!")
                st.download_button(
                    label="Download All Certificates",
                    data=zip_buffer.getvalue(),
                    file_name="certificates.zip",
                    mime="application/zip"
                )

# VERIFY CERTIFICATE TAB

with verify_tab:
    st.header("Verify Certificate")

    # Get Certificate ID from QR URL
    qr_certificate_id = st.query_params.get("certificate_id", "")
    st.write("Enter the Certificate ID to check whether the certificate is valid.")
    certificate_id_input = st.text_input("Certificate ID",value=qr_certificate_id)

    # Automatically verify if opened through QR,
    # otherwise verify when button is clicked
    verify_clicked = st.button("Verify Certificate")
    if qr_certificate_id or verify_clicked:
        if certificate_id_input == "":
            st.warning("Please enter a Certificate ID.")
        elif not os.path.exists(RECORD_FILE):
            st.error("No certificate records found.")
        else:
            certificate_database = pd.read_csv(RECORD_FILE)
            result = certificate_database[certificate_database["Certificate_ID"] == certificate_id_input.strip()]
            if not result.empty:
                participant_name = result.iloc[0]["Name"]
                st.success("Certificate is Valid!")
                st.write(f"*Certificate ID:* {certificate_id_input}")
                st.write(f"*Issued To:* {participant_name}")
            else:
                st.error("Invalid Certificate ID")