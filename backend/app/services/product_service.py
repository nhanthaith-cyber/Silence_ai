from sqlalchemy.orm import Session
from app.models.models import Product, gen_uuid
import json


def search_products(
    db: Session,
    query: str = None,
    category: str = None,
    fit_type: str = None,
    size: str = None,
    min_price: int = None,
    max_price: int = None,
    limit: int = 10
) -> list:
    """Tìm kiếm sản phẩm theo nhiều tiêu chí."""
    q = db.query(Product).filter(Product.is_active == True)  # noqa: E712

    # Lọc theo danh mục
    if category:
        q = q.filter(Product.category == category)

    # Lọc theo form dáng
    if fit_type:
        q = q.filter(Product.fit_type == fit_type)

    # Lọc theo khoảng giá (ưu tiên sale_price nếu có)
    if min_price is not None:
        q = q.filter(
            ((Product.sale_price != None) & (Product.sale_price >= min_price)) |  # noqa: E711
            ((Product.sale_price == None) & (Product.price >= min_price))  # noqa: E711
        )
    if max_price is not None:
        q = q.filter(
            ((Product.sale_price != None) & (Product.sale_price <= max_price)) |  # noqa: E711
            ((Product.sale_price == None) & (Product.price <= max_price))  # noqa: E711
        )

    # Tìm kiếm text trong tên, mô tả, chất liệu
    if query:
        search_term = f"%{query}%"
        q = q.filter(
            Product.name.ilike(search_term) |
            Product.description.ilike(search_term) |
            Product.fabric.ilike(search_term)
        )

    products = q.order_by(Product.created_at.desc()).limit(limit).all()

    # Lọc thêm theo size (cần kiểm tra JSON nên lọc ở Python)
    if size:
        filtered = []
        for p in products:
            try:
                sizes = json.loads(p.sizes_available or '{}')
                if size in sizes and sizes[size] > 0:
                    filtered.append(p)
            except (json.JSONDecodeError, TypeError):
                continue
        products = filtered

    return [product_to_dict(p) for p in products]


def get_product_by_id(db: Session, product_id: str) -> dict | None:
    """Lấy sản phẩm theo ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    return product_to_dict(product) if product else None


def get_product_by_slug(db: Session, slug: str) -> dict | None:
    """Lấy sản phẩm theo slug."""
    product = db.query(Product).filter(Product.slug == slug).first()
    return product_to_dict(product) if product else None

def check_stock(db: Session, product_id: str, size: str) -> dict:
    """Kiểm tra tồn kho cho sản phẩm + size cụ thể."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return {
            "available": False,
            "quantity": 0,
            "product_name": "Không tìm thấy",
            "size": size,
        }

    try:
        sizes = json.loads(product.sizes_available or '{}')
    except (json.JSONDecodeError, TypeError):
        sizes = {}

    quantity = sizes.get(size, 0)
    return {
        "available": quantity > 0,
        "quantity": quantity,
        "product_name": product.name,
        "size": size,
    }



async def check_product_stock(db: Session, query: str) -> str:
    """
    Tìm kiếm thông tin sản phẩm và tồn kho từ phần mềm quản lý kho Nhanh.vn.
    """
    # Bước 1: Trả về kết quả từ Nhanh.vn Adapter (hiện đang dùng mock an toàn nếu chưa cấu hình token thành công)
    inventory_data = await nhanh_adapter.check_inventory(query)
    
    # Bước 2: Format dữ liệu để trả về cho AI đọc
    if inventory_data and "data" in inventory_data:
        results = []
        for item in inventory_data["data"]:
            info = f"Sản phẩm: {item.get('product_name')} (Mã: {item.get('sku')})\n"
            info += "Tồn kho thực tế (Nhanh.vn):\n"
            stock_dict = item.get("available_stock", {})
            for size, qty in stock_dict.items():
                status = "CÒN HÀNG" if qty > 0 else "HẾT HÀNG"
                info += f"  - Size {size}: {qty} chiếc ({status})\n"
            results.append(info)
        
        if results:
            return "KẾT QUẢ KIỂM TRA KHO TỪ NHANH.VN:\n" + "\n".join(results)
    
    return f"Không tìm thấy thông tin tồn kho cho sản phẩm: {query} trên hệ thống Nhanh.vn."


def get_size_recommendation(
    db: Session,
    product_id: str,
    height: int,
    weight: int,
    preferred_fit: str = None
) -> dict:
    """Tư vấn size dựa trên số đo khách hàng và đặc tính sản phẩm."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return {
            "recommended_size": None,
            "fit_description": "Không tìm thấy sản phẩm",
            "alternative": None,
            "notes": None,
        }

    # Bảng size tiêu chuẩn theo chiều cao/cân nặng
    size_ranges = [
        ("S",   155, 160, 45, 52),
        ("M",   160, 168, 52, 62),
        ("L",   168, 175, 62, 72),
        ("XL",  175, 182, 72, 82),
        ("XXL", 180, 200, 80, 120),
    ]

    # Tìm size phù hợp nhất dựa trên height + weight
    recommended = "M"  # Mặc định
    for size_name, h_min, h_max, w_min, w_max in size_ranges:
        if h_min <= height <= h_max and w_min <= weight <= w_max:
            recommended = size_name
            break
    else:
        # Nếu không match chính xác, ưu tiên theo cân nặng
        for size_name, h_min, h_max, w_min, w_max in size_ranges:
            if w_min <= weight <= w_max:
                recommended = size_name
                break

    # Điều chỉnh theo fit_type của sản phẩm
    size_order = ["S", "M", "L", "XL", "XXL"]
    idx = size_order.index(recommended) if recommended in size_order else 1
    product_fit = product.fit_type or "regular"
    fit_adjustment = preferred_fit or product_fit

    if fit_adjustment == "oversized" and idx > 0:
        # Oversized thường rộng sẵn → có thể giảm 1 size
        recommended = size_order[idx - 1]
        fit_desc = "vừa vặn (sản phẩm đã oversized sẵn)"
    elif fit_adjustment == "slim" and idx < len(size_order) - 1:
        # Slim fit ôm sát → có thể cần tăng 1 size nếu thích thoải mái
        fit_desc = "ôm vừa người"
    elif fit_adjustment == "relaxed":
        fit_desc = "thoải mái, rộng rãi"
    else:
        fit_desc = "vừa vặn, thoải mái"

    # Gợi ý size thay thế
    if idx < len(size_order) - 1:
        alternative = f"{size_order[idx + 1]} nếu thích rộng hơn"
    elif idx > 0:
        alternative = f"{size_order[idx - 1]} nếu thích ôm hơn"
    else:
        alternative = None

    # Ghi chú về chất liệu (co rút, co giãn...)
    notes = None
    try:
        fabric_props = json.loads(product.fabric_properties or '{}')
        note_parts = []
        if fabric_props.get("shrinkage"):
            note_parts.append(f"Vải có co rút {fabric_props['shrinkage']} sau giặt lần đầu")
        if fabric_props.get("stretch"):
            note_parts.append("Vải có độ co giãn tốt")
        if note_parts:
            notes = ". ".join(note_parts)
    except (json.JSONDecodeError, TypeError):
        pass

    # Kiểm tra tồn kho size được gợi ý
    try:
        sizes_available = json.loads(product.sizes_available or '{}')
        if recommended not in sizes_available or sizes_available[recommended] <= 0:
            notes = (notes + ". " if notes else "") + f"Lưu ý: Size {recommended} hiện tạm hết hàng"
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "recommended_size": recommended,
        "fit_description": fit_desc,
        "alternative": alternative,
        "notes": notes,
    }


def format_product_for_prompt(product: dict) -> str:
    """Format product info để inject vào AI prompt."""
    if not product:
        return ""

    lines = [f"📦 {product.get('name', 'N/A')}"]

    # Giá
    price = product.get("price", 0)
    sale_price = product.get("sale_price")
    if sale_price and sale_price < price:
        lines.append(f"- Giá: {sale_price:,}₫ (giảm từ {price:,}₫)")
    else:
        lines.append(f"- Giá: {price:,}₫")

    # Size có sẵn
    try:
        sizes = json.loads(product.get("sizes_available", "{}") or "{}")
        available = [f"{s} ({q})" for s, q in sizes.items() if q > 0]
        if available:
            lines.append(f"- Size còn hàng: {', '.join(available)}")
    except (json.JSONDecodeError, TypeError):
        pass

    # Chất liệu
    if product.get("fabric"):
        lines.append(f"- Chất liệu: {product['fabric']}")

    # Form dáng
    if product.get("fit_type"):
        lines.append(f"- Form: {product['fit_type']}")

    # Màu sắc
    if product.get("color"):
        lines.append(f"- Màu: {product['color']}")

    # Hướng dẫn bảo quản
    if product.get("care_instructions"):
        lines.append(f"- Bảo quản: {product['care_instructions']}")

    return "\n".join(lines)


def format_stock_response(stock_result: dict) -> str:
    """Format stock check result thành câu trả lời tự nhiên."""
    if not stock_result:
        return "Không thể kiểm tra tồn kho lúc này."

    name = stock_result.get("product_name", "Sản phẩm")
    size = stock_result.get("size", "")
    quantity = stock_result.get("quantity", 0)
    available = stock_result.get("available", False)

    if available:
        if quantity <= 3:
            return f"✅ {name} size {size} còn hàng nhưng chỉ còn {quantity} sản phẩm. Nhanh tay đặt nha bạn!"
        return f"✅ {name} size {size} vẫn còn hàng ({quantity} sản phẩm). Bạn muốn đặt luôn không ạ?"
    else:
        return f"😔 Tiếc quá, {name} size {size} hiện đang hết hàng. Bạn muốn mình báo khi có hàng lại không?"


def product_to_dict(product: Product) -> dict:
    """Convert SQLAlchemy model to dict."""
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "category": product.category,
        "subcategory": product.subcategory,
        "description": product.description,
        "price": product.price,
        "sale_price": product.sale_price,
        "sizes_available": product.sizes_available,
        "size_chart": product.size_chart,
        "fabric": product.fabric,
        "fabric_properties": product.fabric_properties,
        "fit_type": product.fit_type,
        "color": product.color,
        "images": product.images,
        "care_instructions": product.care_instructions,
        "is_active": product.is_active,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }
