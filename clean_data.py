import re
from faker import Faker

fake = Faker()

def clean_and_fill_placeholders(text):
    text = re.sub(r"\{\{\{+", "{{", text)

    def replace_match(match):
        name = match.group(1).lower()
        if any(word in name for word in ["number", "id", "code"]):
            return fake.numerify("#####")
        elif "name" in name:
            return fake.name()
        elif "email" in name:
            return fake.email()
        elif "phone" in name:
            return fake.phone_number()
        elif "url" in name:
            return fake.url()
        elif any(word in name for word in ["date", "time", "hour", "month", "year"]):
            return fake.date()
        elif "currency" in name:
            return "$"
        elif "amount" in name:
            return str(fake.random_int(min=5, max=500))
        elif "city" in name:
            return fake.city()
        elif "country" in name:
            return fake.country()
        elif any(word in name for word in ["category", "type"]):
            return fake.random_element(elements=("Standard", "Premium", "Basic"))
        else:
            return match.group(0)

    return re.sub(r"\{\{(.*?)\}\}", replace_match, text)


def find_remaining_placeholders(dataset):
    remaining_placeholders = set()

    for row in dataset["train"]:
        cleaned_instruction = clean_and_fill_placeholders(row["instruction"])
        
        remaining_placeholders.update(re.findall(r"\{\{.*?\}\}", cleaned_instruction))
       

    return remaining_placeholders