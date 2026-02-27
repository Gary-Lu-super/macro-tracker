from notion_client import Client
import os
from dotenv import load_dotenv

load_dotenv()
notion = Client(auth=os.environ["NOTION_TOKEN"])
db = notion.databases.retrieve(os.environ["NOTION_DATABASE_ID"])

print("=== 欄位名稱（含引號）===")
for name in db["properties"]:
    print(repr(name))