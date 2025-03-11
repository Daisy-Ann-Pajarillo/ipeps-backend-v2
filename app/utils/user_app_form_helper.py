from datetime import datetime, date

def get_user_data(model, user_id):
    """Fetch all records of a specific model for a user."""
    return model.query.filter_by(user_id=user_id).all()

def exclude_fields(data_list):
    filtered_data = []
    for item in data_list:
            item_dict = item.to_dict()
             # Remove 'id' and 'user_id' fields
            item_dict.pop('id', None)
            item_dict.pop('user_id', None)
            filtered_data.append(item_dict)
    return filtered_data

# def convert_date(date_input):
#     try:
#         if isinstance(date_input, datetime):
#             return date_input.strftime("%Y-%m-%d")
        
#         if isinstance(date_input, date):
#             return date_input.strftime("%Y-%m-%d")
        
#         if isinstance(date_input, (int, float)):
#             return datetime.fromtimestamp(date_input).strftime("%Y-%m-%d")

#         if isinstance(date_input, str):
#             date_obj = dateutil.parser.parse(date_input)
#             return date_obj.strftime("%Y-%m-%d")

#         raise ValueError("Unsupported date format or type")

#     except Exception as e:
#         return f"Error: {e}"


def convert(date_to_convert):
    if date_to_convert:
        try:
            return date_to_convert.strftime("%Y-%m-%d")
        except ValueError:
            return date_to_convert
    return None

def convert_dates(data):
    date_fields = ["date_from", "date_to", "start_date", "end_date", "date", "valid_until", "date_start", "date_end", "date_of_birth", "since_when_looking_for_work", "former_ofw_country_date_return"]
    
    if isinstance(data, list):
        return [convert_dates(item) for item in data]
    elif isinstance(data, dict):
        return {key: (convert(value) if key in date_fields else convert_dates(value)) for key, value in data.items()}
    else:
        return data
