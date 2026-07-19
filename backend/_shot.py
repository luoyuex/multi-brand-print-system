import os
os.chdir("D:/code/HBProject/multi-brand-print-system/backend")
import pymupdf
d = pymupdf.open("_chk.pdf")
p = d[0]
pix = p.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72))
pix.save("_chk.png")
print("saved", pix.width, pix.height)
