import google.generativeai as genai
from google.generativeai.types import content_types
import os
import sys
import random
import sys

# Fix Unicode printing issue on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình API key. Khuyến nghị dùng file .env để bảo mật.
from dotenv import load_dotenv
load_dotenv() # Tự động tải các biến môi trường từ file .env

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# ==========================================
# 1. Định nghĩa 2 Tools (Chức năng thực tế)
# ==========================================
def get_weather(city: str, date: str) -> dict:
    """Lấy thông tin thời tiết cho một thành phố vào một ngày cụ thể."""
    
    # Giả lập dữ liệu thời tiết ngẫu nhiên để giống thật hơn
    temp_high = random.randint(20, 38)
    rain_probability = round(random.uniform(0.0, 1.0), 1)
    
    return {
        "city": city,
        "date": date,
        "temperature_c": [temp_high - 5, temp_high],
        "rain_probability": rain_probability,
    }

def recommend_outfit(temp_high: int, rain_probability: float) -> str:
    """Gợi ý trang phục dựa trên nhiệt độ cao nhất và xác suất mưa."""
    if rain_probability > 0.5:
        return "Áo mỏng, giày dễ khô, mang theo ô gấp."
    if temp_high > 30:
        return "Áo nhẹ, thoáng, ưu tiên vải cotton."
    return "Trang phục thoải mái, có thể mang áo khoác nhẹ."

# Cung cấp tool list cho Gemini
tools = [get_weather, recommend_outfit]
available_tools = {
    "get_weather": get_weather,
    "recommend_outfit": recommend_outfit,
}

# ==========================================
# Vòng lặp Agent (Thought / Action / Observation)
# ==========================================
def run_agent(user_prompt: str):
    print(f"\n[User Goal] {user_prompt}\n")
    print("-" * 50)
    
    # Khởi tạo mô hình
    model = genai.GenerativeModel(
        model_name='gemini-flash-latest',
        tools=tools,
        system_instruction="Bạn là một trợ lý ảo tư vấn trang phục. YÊU CẦU BẮT BUỘC: Bạn CHỈ ĐƯỢC đưa ra câu trả lời cuối cùng sau khi đã gọi tool để lấy dữ liệu thời tiết và gợi ý trang phục."
    )
    
    # Tắt automatic function calling để tự xử lý luồng (Thought -> Action -> Observation)
    chat = model.start_chat(enable_automatic_function_calling=False)
    
    loop_count = 0
    max_loops = 5
    current_input = user_prompt

    while loop_count < max_loops:
        loop_count += 1
        print(f"--- Vòng lặp LLM {loop_count} ---")
        
        # 1. Gửi input cho LLM (User prompt hoặc kết quả của Tool)
        try:
            response = chat.send_message(current_input)
        except Exception as e:
            print(f"[Lỗi API]: Vui lòng đảm bảo bạn đã cung cấp đúng GEMINI_API_KEY. Lỗi: {e}")
            break
        
        # 2. Đọc "Thought" của Agent (nếu Agent in ra text trước khi gọi tool)
        try:
            if response.text:
                print(f"[Thought/LLM Message]: {response.text}")
        except ValueError:
            pass # ValueError xảy ra khi response chỉ chứa function_call mà không có text
            
        # 3. Kiểm tra xem LLM có muốn gọi Tool (Action) hay không
        function_call = None
        if hasattr(response, 'parts'):
            for part in response.parts:
                if getattr(part, 'function_call', None):
                    function_call = part.function_call
                    break

        if function_call:
            func_name = function_call.name
            func_args = {key: val for key, val in function_call.args.items()}
            
            print(f"[Action]: LLM yêu cầu gọi tool `{func_name}` với tham số {func_args}")
            
            # 4. Thực thi Tool bằng Python
            function_to_call = available_tools.get(func_name)
            if function_to_call:
                result = function_to_call(**func_args)
                
                # 5. In ra kết quả (Observation)
                print(f"[Observation]: Kết quả từ `{func_name}` là: {result}")
                
                # Format kết quả để trả lại cho mô hình (đóng vai trò là observation cho vòng lặp tiếp theo)
                current_input = genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=func_name,
                        response={"result": result}
                    )
                )
            else:
                print(f"[Error]: Tool {func_name} không tồn tại!")
                break
        else:
            # Nếu không có yêu cầu gọi hàm nào, thì đây là Final Answer
            print(f"\n[Final Answer]: {response.text}\n")
            break
            
        print("-" * 50)

if __name__ == "__main__":
    print("🤖 Xin chào! Tôi là trợ lý ảo tư vấn trang phục dựa trên thời tiết.")
    print("💡 Hãy nhập câu hỏi của bạn (VD: 'Thời tiết Đà Lạt hôm nay thế nào, tôi nên mặc gì?')")
    print("🚪 Gõ 'quit' hoặc 'exit' để thoát.\n")
    
    while True:
        user_input = input("\nBạn: ")
        if user_input.lower() in ['quit', 'exit']:
            print("Tạm biệt!")
            break
        
        if user_input.strip() == "":
            continue
            
        run_agent(user_input)
