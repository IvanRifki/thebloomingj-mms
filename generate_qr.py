import qrcode
import os

daftar_tiket = ["001", "002", "003", "004", "005", "006", "007", "008", "009", "010", "011", "012", "013", "014", "015", "016", "017", "018", "019", "020", "021", "022", "023", "024", "025", "026", "027", "028", "029", "030", "031", "032", "033", "034", "035", "036",
                "037", "038", "039", "040", "041", "042", "043", "044", "045", "046", "047", "048", "049", "050", "051", "052", "053", "054", "055", "056", "057", "058", "059", "060", "061", "062", "063", "064", "065", "066", "067", "068", "069", "070"]


if not os.path.exists('cetak_tiket'):
    os.makedirs('cetak_tiket')

print("Sedang membuat QR Code...")

for kode in daftar_tiket:

    link = f"http://127.0.0.1:5000/scan/{kode}"

    # Buat QR Code
    img = qrcode.make(link)

    # Simpan jadi file gambar
    img.save(f"cetak_tiket/tiket_{kode}.png")


print("\nSelesai! Cek folder 'cetak_tiket' di komputer kamu.")
