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