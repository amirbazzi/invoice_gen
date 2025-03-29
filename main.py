import os
import pathlib
from datetime import date
import streamlit as st
from fpdf import FPDF

# -------------------------------------------------------------------
# Configuration & Constants
# -------------------------------------------------------------------
FONT_BOOKMAN_REGULAR = "BOOKOS.TTF"  # Bookman Old Style Regular
FONT_BOOKMAN_BOLD = "BOOKOSB.TTF"     # Bookman Old Style Bold
LOGO_PATH = "ashi_logo.jpg"
CURRENCY_SYMBOL = "€"

# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------
def parse_int_with_commas(text: str) -> int:
    """Parse a string like '12,300' into an integer 12300."""
    text = text.replace(",", "").strip()
    return int(text) if text.isdigit() else 0

def ordinal(n: int) -> str:
    """Convert a 0-based index to an ordinal word: first, second, etc."""
    ordinals = ["first", "second", "third", "fourth", "fifth", 
                "sixth", "seventh", "eighth", "ninth", "tenth"]
    return ordinals[n] if n < len(ordinals) else f"{n+1}th"

def safe_cell(pdf, w, h, txt, border=0, new_line=False, align="", fill=False, link=""):
    """
    Wrapper for pdf.cell() that attempts to use new_x/new_y parameters.
    If those are unsupported (raising a TypeError), it falls back to using ln.
    """
    try:
        if new_line:
            # Try using new_x and new_y (supported in FPDF>=2.5.2)
            return pdf.cell(w, h, txt, border=border, new_x="LMARGIN", new_y="NEXT",
                            align=align, fill=fill, link=link)
        else:
            return pdf.cell(w, h, txt, border=border, ln=0, align=align, fill=fill, link=link)
    except TypeError:
        # Fallback to using ln parameter
        if new_line:
            return pdf.cell(w, h, txt, border=border, ln=1, align=align, fill=fill, link=link)
        else:
            return pdf.cell(w, h, txt, border=border, ln=0, align=align, fill=fill, link=link)

# -------------------------------------------------------------------
# PDF Initialization
# -------------------------------------------------------------------
def init_pdf() -> FPDF:
    """Initialize FPDF and register Bookman fonts."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    st.write("### Font Path Debugging")
    st.write("Current working directory:", os.getcwd())
    st.write("FONT_BOOKMAN_REGULAR path:", FONT_BOOKMAN_REGULAR, "Exists?", os.path.exists(FONT_BOOKMAN_REGULAR))
    st.write("FONT_BOOKMAN_BOLD path:", FONT_BOOKMAN_BOLD, "Exists?", os.path.exists(FONT_BOOKMAN_BOLD))
    
    try:
        # Add Bookman fonts (ensure these TTF files exist)
        pdf.add_font("Bookman", "", FONT_BOOKMAN_REGULAR, uni=True)
        pdf.add_font("Bookman", "B", FONT_BOOKMAN_BOLD, uni=True)
        pdf.set_font("Bookman", size=10)
        return pdf
    except Exception as e:
        st.error(f"PDF initialization failed: {e}")
        return None

# -------------------------------------------------------------------
# PDF Generation
# -------------------------------------------------------------------
def create_invoice_pdf(invoice_data: dict) -> bytes:
    """
    Creates an invoice PDF with:
      1) Header (logo, company info, invoice details, client info)
      2) Items table with totals and VAT
      3) Payment schedule table
      4) Bank details in a 4-column layout
      5) Terms & Conditions and final message
    """
    pdf = init_pdf()
    if not pdf:
        return None

    # Set margins and auto page break
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=10)

    try:
        # --- 1) HEADER ---
        if os.path.exists(LOGO_PATH):
            pdf.image(LOGO_PATH, x=(210 - 30) / 2, y=10, w=30)
        else:
            st.warning(f"Logo file not found: {LOGO_PATH}")
        pdf.set_y(30)
        
        # Company Info (left)
        pdf.set_font("Bookman", "B", 10)
        pdf.set_xy(10, 30)
        safe_cell(pdf, 60, 5, "ASHI STUDIO SAS", new_line=True)
        
        pdf.set_font("Bookman", "", 9)
        pdf.set_x(10)
        safe_cell(pdf, 60, 5, "9 AVENUE HOCHE", new_line=True)
        pdf.set_x(10)
        safe_cell(pdf, 60, 5, "75008 PARIS, FRANCE", new_line=True)
        
        # Invoice Number & Date (right)
        pdf.set_xy(140, 30)
        inv_text = (f"Invoice Number: {invoice_data['invoice_number']}\n\n"
                    f"Date: {invoice_data['invoice_date']}")
        pdf.multi_cell(60, 5, inv_text, align="R")
        pdf.ln(10)
        
        # Client Info
        pdf.set_font("Bookman", "B", 10)
        safe_cell(pdf, 0, 5, "Client Information", new_line=True)
        pdf.set_font("Bookman", "", 10)
        safe_cell(pdf, 0, 5, f"Name: {invoice_data['client_name']}", new_line=True)
        safe_cell(pdf, 0, 5, f"Country: {invoice_data['country']}", new_line=True)
        safe_cell(pdf, 0, 5, f"Phone: {invoice_data['phone']}", new_line=True)
        pdf.ln(5)
        
        # --- 2) ITEMS TABLE ---
        col_desc_w = 70
        col_price_w = 50
        col_paid_w = 60

        pdf.set_font("Bookman", "B", 10)
        safe_cell(pdf, col_desc_w, 6, "DESCRIPTION", border=1, new_line=False, align="C")
        safe_cell(pdf, col_price_w, 6, "TOTAL PRICE", border=1, new_line=False, align="C")
        safe_cell(pdf, col_paid_w, 6, "TO BE PAID", border=1, new_line=True, align="C")
        
        pdf.set_font("Bookman", "", 10)
        sum_price = 0
        sum_paid = 0
        for item in invoice_data["items"]:
            desc = item["description"]
            price = item["price"]
            paid = item["paid"]
            sum_price += price
            sum_paid += paid

            safe_cell(pdf, col_desc_w, 6, desc, border=1, new_line=False, align="L")
            safe_cell(pdf, col_price_w, 6, f"{price:,d} {CURRENCY_SYMBOL}", border=1, new_line=False, align="L")
            safe_cell(pdf, col_paid_w, 6, f"{paid:,d} {CURRENCY_SYMBOL}", border=1, new_line=True, align="R")
        
        # Summation row
        safe_cell(pdf, col_desc_w, 6, "", border=0, new_line=False)
        safe_cell(pdf, col_price_w, 6, f"{sum_price:,d} {CURRENCY_SYMBOL}", border=0, new_line=False, align="L")
        safe_cell(pdf, col_paid_w, 6, f"{sum_paid:,d} {CURRENCY_SYMBOL}", border=0, new_line=True, align="R")
        
        # VAT and Final Total (placed under the third column)
        vat = invoice_data["vat"]
        final_total = sum_paid + vat
        label_w = 20
        val_w = col_paid_w - label_w

        safe_cell(pdf, col_desc_w, 6, "", border=0, new_line=False)
        safe_cell(pdf, col_price_w, 6, "", border=0, new_line=False)
        safe_cell(pdf, label_w, 6, "VAT", border=0, new_line=False, align="L")
        safe_cell(pdf, val_w, 6, f"{vat:,d}", border=0, new_line=True, align="R")

        safe_cell(pdf, col_desc_w, 6, "", border=0, new_line=False)
        safe_cell(pdf, col_price_w, 6, "", border=0, new_line=False)
        safe_cell(pdf, label_w, 6, "Total", border=0, new_line=False, align="L")
        safe_cell(pdf, val_w, 6, f"{final_total:,d} {CURRENCY_SYMBOL}", border=0, new_line=True, align="R")
        pdf.ln(1)
        
        # --- 3) PAYMENT SCHEDULE ---
        pdf.set_font("Bookman", "B", 10)
        safe_cell(pdf, 60, 6, "PAYMENT", border=1, new_line=False, align="C")
        safe_cell(pdf, 40, 6, "DATE", border=1, new_line=False, align="C")
        safe_cell(pdf, 40, 6, "PERCENTAGE", border=1, new_line=False, align="C")
        safe_cell(pdf, 40, 6, "AMOUNT", border=1, new_line=True, align="C")
        
        pdf.set_font("Bookman", "", 10)
        sum_price_local = sum_price  # Payment plan must match the total PRICE
        for idx, pay in enumerate(invoice_data["payments"]):
            pay_name = pay["name"] or "N/A"
            pay_date = pay["date"] or ""
            perc = pay["percentage"]
            amt = pay["amount"]

            if perc == 0 and amt != 0:
                perc = int(round(amt / sum_price_local * 100))
            elif amt == 0 and perc != 0:
                amt = int(round(perc / 100 * sum_price_local))

            safe_cell(pdf, 60, 6, pay_name, border=1, new_line=False, align="L")
            safe_cell(pdf, 40, 6, pay_date, border=1, new_line=False, align="L")
            safe_cell(pdf, 40, 6, f"{perc:,d}%", border=1, new_line=False, align="L")
            safe_cell(pdf, 40, 6, f"{amt:,d} {CURRENCY_SYMBOL}", border=1, new_line=True, align="L")

            invoice_data["payments"][idx]["percentage"] = perc
            invoice_data["payments"][idx]["amount"] = amt
        
        pdf.ln(1)
        y_line = pdf.get_y()
        pdf.line(10, y_line, 200, y_line)
        pdf.ln(1)
        
        # --- 4) BANK DETAILS (4 Columns) ---
        def print_bank_column(pdf, start_x, start_y, col_width, data, title_size=8, detail_size=8):
            current_y = start_y
            for (title, detail) in data:
                pdf.set_xy(start_x, current_y)
                pdf.set_font("Bookman", "BU", title_size)
                pdf.multi_cell(col_width, 5, title, 0, "L")
                current_y = pdf.get_y()
                pdf.set_xy(start_x, current_y)
                pdf.set_font("Bookman", "", detail_size)
                pdf.multi_cell(col_width, 5, detail, 0, "L")
                current_y = pdf.get_y()
            return current_y
        
        def example_bank_details_4columns(pdf):
            pdf.set_font("Bookman", "B", 10)
            safe_cell(pdf, 0, 5, "Bank Transfer Details:", new_line=True)
            pdf.ln(2)
            
            col1_data = [
                ("BENEFICIARY:", "ASHI STUDIO SAS\n9 AVENUE HOCHE\n75008 PARIS, FRANCE"),
                ("REGISTRATION number:", "922 266 788 00012"),
                ("VAT:", "FR21922266788"),
            ]
            col2_data = [
                ("BANK NAME:", "BNP PARIBAS"),
                ("AGENCY ADDRESS:", "Agency Paris Turenne"),
                ("AGENCY CODE:", "00823"),
            ]
            col3_data = [
                ("ACCOUNT CURRENCY:", "EUR (Euro)"),
                ("IBAN:", "FR76 3000 4008 2300 0108 9656 803"),
                ("RIB:", "03"),
            ]
            col4_data = [
                ("SWIFT:", "BNPAFRPPXXX"),
                ("ACCOUNT N°:", "00010896568"),
                ("BANK CODE:", "30004"),
            ]
            
            start_x = 10
            start_y = pdf.get_y()
            col_width = 45
            col_spacing = 10
            
            col1_end = print_bank_column(pdf, start_x, start_y, col_width, col1_data)
            col2_end = print_bank_column(pdf, start_x + col_width + col_spacing, start_y, col_width, col2_data)
            col3_end = print_bank_column(pdf, start_x + 2*(col_width + col_spacing), start_y, col_width, col3_data)
            col4_end = print_bank_column(pdf, start_x + 3*(col_width + col_spacing), start_y, col_width, col4_data)
            final_y = max(col1_end, col2_end, col3_end, col4_end)
            pdf.set_y(final_y + 5)
            y_line = pdf.get_y()
            pdf.line(10, y_line, 200, y_line)
            pdf.ln(3)
        
        example_bank_details_4columns(pdf)
        
        # --- 5) TERMS & CONDITIONS ---
        pdf.set_font("Bookman", "B", 10)
        safe_cell(pdf, 0, 5, "Terms & Conditions", new_line=True)
        pdf.ln(3)
        
        pdf.set_font("Bookman", "", 8)
        for i, pay in enumerate(invoice_data["payments"]):
            pdf.write(5, f"• A {ordinal(i)} payment of ")
            pdf.set_font("Bookman", "B", 8)
            pdf.write(5, f"{pay['percentage']}%")
            pdf.set_font("Bookman", "", 8)
            pdf.write(5, " of the total price is required")
            if pay["name"]:
                pdf.write(5, f" as {pay['name']}")
            if pay["description"]:
                pdf.write(5, f" ({pay['description']})")
            pdf.write(5, "\n")
        
        standard_terms = [
            "• As per the company policy, once a dress is purchased, it is not subject to return or refund",
            "• Once the purchase details and samples are approved by the client, the dress is not subject to any changes",
            "• The delivery date is scheduled as per the agreement with the sales team upon order confirmation; in case of any date change or event cancellation, Ashi Studio will be working according to the initial date provided",
            "• Any addition to the dress, requested by the client, will be charged separately",
            "• After doing the final fitting and dress adjustments, once the dress is received, any changes requested are not covered by Ashi Studio and are subject to additional payments",
            "• Fittings and delivery will be in the client country of origin or in AshI STUDIO showroom in Paris; any changes in the destination will be at the cost of the client"
        ]
        for idx, term in enumerate(standard_terms):
            if idx in [0, 1]:
                pdf.set_font("Bookman", "B", 8)
            else:
                pdf.set_font("Bookman", "", 8)
            pdf.write(5, term + "\n")
        
        pdf.ln(3)
        y_line = pdf.get_y()
        pdf.line(10, y_line, 200, y_line)
        pdf.ln(3)
        
        pdf.set_font("Bookman", "B", 8)
        safe_cell(pdf, 0, 5, "THANK YOU FOR CHOOSING ASHI STUDIO", new_line=True, align="C")
        safe_cell(pdf, 0, 5, "WWW.ASHISTUDIO.COM", new_line=True, align="C")
        
        # Return the PDF as bytes (no extra encoding required)
        return bytes(pdf.output(dest="S"))

    
    except Exception as e:
        st.error(f"Failed to generate PDF: {e}")
        return None

# -------------------------------------------------------------------
# Streamlit App Layout
# -------------------------------------------------------------------
st.title("ASHI STUDIO Invoice Generator")
st.write("**Prices** must sum up for Payment Plan to match the **Total Price** (not the total to be paid).")

# --- 1) Client & Invoice Information ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("Client Information")
    invoice_number = st.text_input("Invoice Number", "369/2025")
    client_name = st.text_input("Client Name", "Pr Noura Abdullah Faisal")
    country = st.text_input("Country", "Kuwait")
    phone = st.text_input("Phone", "+965 1234 5678")
with col2:
    st.subheader("Invoice Details")
    invoice_date = st.date_input("Invoice Date", value=date.today())
    vat_str = st.text_input("VAT (use commas)", "0")

# --- 2) Invoice Items ---
st.subheader("Invoice Items")
num_items = st.number_input("Number of Items", 1, 20, 2)
items = []
for i in range(int(num_items)):
    with st.expander(f"Item {i+1}", expanded=(i == 0)):
        desc = st.text_input(f"Description {i+1}", f"Item {i+1}", key=f"desc_{i}")
        price_str = st.text_input(f"Total Price {i+1} (use commas)", "0", key=f"price_{i}")
        paid_str = st.text_input(f"To Be Paid {i+1} (use commas)", "0", key=f"paid_{i}")
        price_val = parse_int_with_commas(price_str)
        paid_val = parse_int_with_commas(paid_str)
        items.append({"description": desc, "price": price_val, "paid": paid_val})

sum_price = sum(item["price"] for item in items)
sum_paid = sum(item["paid"] for item in items)
vat_val = parse_int_with_commas(vat_str)
final_total_paid = sum_paid + vat_val

st.write("---")
st.write(f"**Total Price:** {sum_price:,d} {CURRENCY_SYMBOL}")
st.write(f"**Total To Be Paid:** {sum_paid:,d} {CURRENCY_SYMBOL}")
st.write(f"**VAT:** {vat_val:,d} {CURRENCY_SYMBOL}")
st.write(f"**Final To Be Paid (with VAT):** {final_total_paid:,d} {CURRENCY_SYMBOL}")
st.write("---")

# --- 3) Payment Schedule ---
st.subheader("Payment Schedule (must sum up to Total Price)")
num_payments = st.number_input("Number of Payments", 1, 10, 3)
payments = []
default_names = ["Down Payment", "Fitting Payment", "Closing Payment"]
default_perc = [50, 30, 20]
for i in range(int(num_payments)):
    with st.expander(f"Payment {i+1}", expanded=(i < 3)):
        if i < 3:
            pay_name = st.selectbox(
                f"Payment Title {i+1}",
                ["down payment", "fitting payment", "closing payment", "full payment"],
                key=f"pay_name_{i}",
                index=["down payment", "fitting payment", "closing payment", "full payment"].index(default_names[i].lower())
            )
        else:
            pay_name = st.selectbox(
                f"Payment Title {i+1}",
                ["down payment", "fitting payment", "closing payment", "full payment"],
                key=f"pay_name_{i}"
            )
        date_enabled = st.checkbox(f"Set date for Payment {i+1}", value=(i == 0), key=f"chk_date_{i}")
        pay_date = st.date_input(f"Date {i+1}", value=date.today(), key=f"pay_date_{i}") if date_enabled else ""
        col_perc, col_amt = st.columns(2)
        with col_perc:
            suggested_perc = str(default_perc[i]) if i < len(default_perc) else "0"
            perc_str = st.text_input(f"Percentage {i+1}", suggested_perc, key=f"perc_{i}")
        with col_amt:
            amt_str = st.text_input(f"Amount {i+1} (use commas)", "0", key=f"amt_{i}")
        pay_desc = st.text_input(f"Description {i+1}", "", key=f"desc_pay_{i}")
        perc_val = parse_int_with_commas(perc_str)
        amt_val = parse_int_with_commas(amt_str)
        payments.append({
            "name": pay_name,
            "date": pay_date.strftime("%d-%m-%Y") if date_enabled else "",
            "percentage": perc_val,
            "amount": amt_val,
            "description": pay_desc
        })

if "pdf_data" not in st.session_state:
    st.session_state.pdf_data = None

if st.button("Generate Invoice"):
    total_percent = sum(p["percentage"] for p in payments)
    total_amount = sum(p["amount"] for p in payments)
    validation_errors = []
    if not (total_percent == 100 or total_amount == sum_price):
        validation_errors.append(
            f"Either sum of payment percentages must be 100%, or sum of payment amounts must equal total price ({sum_price:,d} {CURRENCY_SYMBOL})."
        )
    for p in payments:
        if p["percentage"] == 0 and p["amount"] == 0:
            validation_errors.append("Each payment must have a non-zero percentage or a non-zero amount.")
            break
    if validation_errors:
        for err in validation_errors:
            st.error(err)
        st.session_state.pdf_data = None
    else:
        invoice_data = {
            "invoice_number": invoice_number,
            "invoice_date": invoice_date.strftime("%d/%m/%Y"),
            "client_name": client_name,
            "country": country,
            "phone": phone,
            "items": items,
            "vat": vat_val,
            "payments": payments
        }
        pdf_bytes = create_invoice_pdf(invoice_data)
        st.session_state.pdf_data = {
            "bytes": pdf_bytes,
            "invoice_number": invoice_number
        } if pdf_bytes else None

if st.session_state.pdf_data:
    st.success("Invoice ready for download!")
    st.download_button(
        label="Download Invoice",
        data=st.session_state.pdf_data["bytes"],
        file_name=f"ashi_invoice_{st.session_state.pdf_data['invoice_number'].replace('/', '_')}.pdf",
        mime="application/pdf"
    )
