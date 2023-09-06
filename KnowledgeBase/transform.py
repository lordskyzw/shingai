from docx import Document
import pandas as pd

doc = Document(docx="Catalog 2023.docx")
table = doc.tables[0]
data = [[cell.text for cell in row.cells] for row in table.rows]
df = pd.DataFrame(data)

df.to_excel("catalog.xlsx", index=False)
