#!/bin/bash

# --- إعدادات المستودع (يجب تعديلها قبل الرفع) ---
# ضع اسم حسابك واسم المستودع هنا ليقوم السكربت بتحميل الملفات تلقائياً
GITHUB_USER="YOUR_GITHUB_USER"
REPO_NAME="YOUR_REPO_NAME"
BRANCH="main"

# --- بداية التثبيت ---
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}>>> بدء تثبيت بوت النشر التلقائي...${NC}"

# 1. تحديث النظام
sudo apt update -qq && sudo apt install python3-pip python3-venv git -y -qq

# 2. جلب الملفات
cd /root
if [ -d "$REPO_NAME" ]; then
    rm -rf "$REPO_NAME"
fi

echo -e "${GREEN}>>> جاري تحميل الملفات من GitHub...${NC}"
git clone "https://github.com/$GITHUB_USER/$REPO_NAME.git"
cd "$REPO_NAME"

# 3. تثبيت المكتبات
echo -e "${GREEN}>>> إعداد بيئة بايثون...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. طلب المعلومات من المستخدم
echo -e "${CYAN}----------------------------------------${NC}"
read -p "أدخل توكن البوت (Bot Token): " BOT_TOKEN
read -p "أدخل آيدي الأدمن (Admin ID): " ADMIN_ID
echo -e "${CYAN}----------------------------------------${NC}"

# حفظ المعلومات
echo "TOKEN=$BOT_TOKEN" > .env
echo "ADMIN_ID=$ADMIN_ID" >> .env

# 5. إنشاء خدمة Systemd
SERVICE_FILE="/etc/systemd/system/${REPO_NAME}.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Telegram Auto Poster ($REPO_NAME)
After=network.target

[Service]
User=root
WorkingDirectory=/root/$REPO_NAME
ExecStart=/root/$REPO_NAME/venv/bin/python3 main_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 6. التشغيل
sudo systemctl daemon-reload
sudo systemctl enable "${REPO_NAME}.service"
sudo systemctl start "${REPO_NAME}.service"

echo -e "${GREEN}✅ تم التثبيت والتشغيل بنجاح!${NC}"
echo -e "البوت يعمل الآن في الخلفية."
