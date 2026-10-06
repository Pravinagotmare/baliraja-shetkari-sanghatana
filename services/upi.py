import qrcode
from urllib.parse import quote

def create_upi_qr(upi_id, name, amount, note, output):
    uri = (
        "upi://pay?"
        f"pa={quote(upi_id)}&"
        f"pn={quote(name)}&"
        f"am={amount:.2f}&"
        "cu=INR&"
        f"tn={quote(note)}"
    )
    image = qrcode.make(uri)
    image.save(output)
    return uri
