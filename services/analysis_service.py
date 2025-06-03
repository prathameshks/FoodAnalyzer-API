from sqlalchemy.orm import Session
from db.models import Marker, Product
from utils.analysis_utils import format_product_analysis_response
from utils.logger_manager import log_info, log_error

def get_product_data_by_marker_id(db: Session, target_id: str):
    """
    Retrieves product analysis and ingredient information by marker ID.

    Args:
        db: The database session.
        target_id: The target ID from the marker table.

    Returns:
        A dictionary containing product analysis and ingredient information,
        or None if no product is found.
    """
    log_info(f"Attempting to retrieve product data for marker ID: {target_id}")
    try:
        # Find the marker with the given target_id
        marker = db.query(Marker).filter(Marker.target_id == target_id).first()

        if not marker:
            log_info(f"No marker found for target ID: {target_id}")
            return {"found": False, "message": f"No product found for marker ID: {target_id}"}

        # Get the product associated with the marker
        product = db.query(Product).filter(Product.id == marker.product_id).first()

        if not product:
            log_info(f"No product found for product_id: {marker.product_id} linked to marker ID: {target_id}")
            return {"found": False, "message": f"No product found for marker ID: {target_id}"}

        log_info(f"Product found for marker ID {target_id}: {product.name}")

        # Format the response using the utility function
        response_data = format_product_analysis_response(product)

        return response_data

    except Exception as e:
        log_error(f"Error retrieving product data for marker ID {target_id}: {str(e)}", e)
        # Return a structured error response
        return {"found": False, "message": "An error occurred while retrieving product data."}