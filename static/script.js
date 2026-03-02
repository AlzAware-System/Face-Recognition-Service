document.addEventListener("DOMContentLoaded", () => {

  const POLLING_INTERVAL = 300; // 300 ميللي ثانية

  // العناصر
  const tabLinks = document.querySelectorAll(".tab-link");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const faceResultText = document.getElementById("face-result-text");
  const medResultText = document.getElementById("med-result-text");
  const medCard = document.getElementById("med-feed-card");

  let lastFaceResult = "Connecting...";
  let lastMedResult = "Connecting...";

  // --- 1. دالة لتبليغ السيرفر بتغيير الوضع ---
  async function switchServerMode(modeName) {
    try {
      console.log(`Requesting server to switch to mode: ${modeName}...`);
      await fetch("/api/set_active_mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: modeName }),
      });
    } catch (error) {
      console.error("Failed to switch mode:", error);
    }
  }

  // --- 2. منطق التنقل (معدل) ---
  tabLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();

      // تغيير التبويب في الواجهة (UI)
      tabLinks.forEach(l => l.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));
      link.classList.add("active");
      const activeTabId = link.getAttribute("data-tab");
      document.getElementById(activeTabId).classList.add("active");

      // ### التعديل هنا: إبلاغ السيرفر بتغيير المود ###
      if (activeTabId === "face-rec-tab") {
        switchServerMode("face"); // شغل الوجوه، وقف الأدوية
      } else if (activeTabId === "med-rec-tab") {
        switchServerMode("object"); // شغل الأدوية، وقف الوجوه
      }
    });
  });

  // --- 3. منطق المراقبة (Polling) ---
  async function getLatestResults() {
    try {
      const response = await fetch("/api/get_latest_results");
      if (!response.ok) throw new Error("Server unreachable");

      const data = await response.json();

      // تحديث الوجوه (فقط لو السيرفر باعت نتيجة حقيقية مش Paused)
      if (data.face_prediction && data.face_prediction !== "Paused") {
        // تحديث النص فقط لو اتغير عشان نمنع الرعشة
        if (data.face_prediction !== lastFaceResult) {
           faceResultText.textContent = data.face_prediction;
           lastFaceResult = data.face_prediction;
        }
      }

      // تحديث الأدوية (فقط لو مش Paused)
      if (data.object_prediction && data.object_prediction !== "Paused") {
        if (data.object_prediction !== lastMedResult) {
            medResultText.textContent = data.object_prediction;
            lastMedResult = data.object_prediction;

            // تلوين الكارت حسب النوع
            medResultText.classList.remove("type-medicine", "type-object");
            medCard.classList.remove("border-medicine", "border-object", "border-none");

            if (data.object_type === 'medicine') {
              medResultText.classList.add("type-medicine");
              medCard.classList.add("border-medicine");
            } else if (data.object_type === 'object') {
              medResultText.classList.add("type-object");
              medCard.classList.add("border-object");
            } else {
              medCard.classList.add("border-none");
            }
        }
      }

    } catch (error) {
      console.error("Error in polling loop:", error.message);
      // في حالة الخطأ، لا نغير النص فوراً للحفاظ على آخر نتيجة
    }
  }

  // --- 4. بدء التشغيل ---
  setInterval(getLatestResults, POLLING_INTERVAL);

  // افتراضياً: تأكد إن السيرفر يبدأ بوضع الوجوه (لأن ده التاب الافتراضي)
  switchServerMode("face");
});