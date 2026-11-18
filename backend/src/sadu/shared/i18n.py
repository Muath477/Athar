from typing import Any

MESSAGES: dict[str, dict[str, str]] = {
    "problem.validation_failed.title": {"ar": "بيانات غير صالحة", "en": "Invalid request"},
    "problem.validation_failed.detail": {
        "ar": "راجع الحقول المذكورة وأعد المحاولة.",
        "en": "Check the listed fields and try again.",
    },
    "problem.not_found.title": {"ar": "غير موجود", "en": "Not found"},
    "problem.not_found.detail": {"ar": "العنصر المطلوب غير موجود.", "en": "The item does not exist."},
    "problem.http_error.title": {"ar": "تعذر تنفيذ الطلب", "en": "Request failed"},
    "problem.http_error.detail": {"ar": "تعذر تنفيذ الطلب.", "en": "The request could not be completed."},
    "problem.internal_error.title": {"ar": "خطأ في الخادم", "en": "Server error"},
    "problem.internal_error.detail": {
        "ar": "حدث خطأ غير متوقع. أعد المحاولة لاحقًا.",
        "en": "An unexpected error occurred. Try again later.",
    },
    "problem.upload_too_large.title": {"ar": "الصورة كبيرة جدًا", "en": "Photo is too large"},
    "problem.upload_too_large.detail": {
        "ar": "الحد الأقصى {max_mb} ميغابايت.",
        "en": "Maximum size is {max_mb} MB.",
    },
    "problem.unsupported_image.title": {"ar": "نوع الصورة غير مدعوم", "en": "Unsupported image"},
    "problem.unsupported_image.detail": {
        "ar": "أرسل صورة بصيغة JPEG أو PNG.",
        "en": "Send a JPEG or PNG photo.",
    },
    "problem.idempotency_key_missing.title": {"ar": "مفتاح التكرار مفقود", "en": "Idempotency key missing"},
    "problem.idempotency_key_missing.detail": {
        "ar": "أرسل الترويسة Idempotency-Key بقيمة UUID.",
        "en": "Send an Idempotency-Key header with a UUID.",
    },
    "problem.idempotency_key_reused.title": {"ar": "مفتاح مستخدم", "en": "Idempotency key reused"},
    "problem.idempotency_key_reused.detail": {
        "ar": "استُخدم هذا المفتاح لطلب مختلف.",
        "en": "This key was already used for a different request.",
    },
    "problem.rate_limited.title": {"ar": "طلبات كثيرة", "en": "Too many requests"},
    "problem.rate_limited.detail": {
        "ar": "انتظر {retry_after_s} ثانية ثم أعد المحاولة.",
        "en": "Wait {retry_after_s} seconds and try again.",
    },
    "problem.not_authenticated.title": {"ar": "يلزم تسجيل الدخول", "en": "Login required"},
    "problem.not_authenticated.detail": {"ar": "سجّل الدخول للمتابعة.", "en": "Log in to continue."},
    "problem.invalid_credentials.title": {"ar": "بيانات الدخول غير صحيحة", "en": "Invalid credentials"},
    "problem.invalid_credentials.detail": {
        "ar": "البريد أو كلمة المرور غير صحيحة.",
        "en": "Email or password is incorrect.",
    },
    "problem.account_locked.title": {"ar": "الحساب مقفل مؤقتًا", "en": "Account temporarily locked"},
    "problem.account_locked.detail": {
        "ar": "حاول بعد {minutes} دقيقة.",
        "en": "Try again in {minutes} minutes.",
    },
    "problem.forbidden.title": {"ar": "غير مسموح", "en": "Forbidden"},
    "problem.forbidden.detail": {"ar": "لا تملك صلاحية لهذا الإجراء.", "en": "You cannot do this."},
    "problem.csrf_failed.title": {"ar": "طلب مرفوض", "en": "Request rejected"},
    "problem.csrf_failed.detail": {"ar": "حدّث الصفحة وأعد المحاولة.", "en": "Reload the page and try again."},
    "problem.observation_not_waiting.title": {"ar": "لا يوجد سؤال", "en": "No open question"},
    "problem.observation_not_waiting.detail": {
        "ar": "هذه المشاركة لا تنتظر إجابة.",
        "en": "This observation is not waiting for an answer.",
    },
    "problem.finding_not_in_review.title": {"ar": "ليست بانتظار المراجعة", "en": "Not in review"},
    "problem.finding_not_in_review.detail": {
        "ar": "هذه الملاحظة لا تنتظر مراجعة.",
        "en": "This finding is not waiting for review.",
    },
    "problem.map_already_approved.title": {"ar": "المخطط معتمد", "en": "Map already approved"},
    "problem.map_already_approved.detail": {
        "ar": "لا يمكن تعديل مخطط معتمد. أنشئ مخططًا جديدًا للجدار.",
        "en": "An approved map cannot be changed. Create a new map for the wall.",
    },
    "problem.photo_unusable.title": {"ar": "الصورة غير صالحة للتحليل", "en": "Photo cannot be analysed"},
    "problem.photo_unusable.detail": {"ar": "{reason_ar}", "en": "{reason_en}"},
    "problem.invalid_corners.title": {"ar": "زوايا الجدار غير صحيحة", "en": "Invalid wall corners"},
    "problem.invalid_corners.detail": {
        "ar": "حدد زوايا الجدار الأربع داخل الصورة بحيث تكوّن شكلًا رباعيًا غير متقاطع.",
        "en": "Mark the four wall corners inside the photo so they form a simple quadrilateral.",
    },
    "problem.wall_size_required.title": {"ar": "مقاس الجدار مطلوب", "en": "Wall size required"},
    "problem.wall_size_required.detail": {
        "ar": "اختر واجهة مسجلة أو أدخل اسم الجدار وعرضه وارتفاعه بالمتر.",
        "en": "Pick a registered facade or enter the wall name, width and height in metres.",
    },
    "problem.photo_required.title": {"ar": "الصورة مطلوبة", "en": "Photo required"},
    "problem.photo_required.detail": {
        "ar": "أرفق صورة الجدار أو اختر مشاركة زائر.",
        "en": "Attach a wall photo or pick a visitor observation.",
    },
    "problem.empty_message.title": {"ar": "الرسالة فارغة", "en": "Empty message"},
    "problem.empty_message.detail": {
        "ar": "اكتب سؤالك أو أرفق صورة أو ملف PDF.",
        "en": "Write a question or attach a photo or PDF.",
    },
    "problem.too_many_attachments.title": {"ar": "مرفقات كثيرة", "en": "Too many attachments"},
    "problem.too_many_attachments.detail": {
        "ar": "أرفق {max_files} ملفات على الأكثر في الرسالة الواحدة.",
        "en": "Attach at most {max_files} files per message.",
    },
    "problem.assistant_busy.title": {"ar": "المساعد يرد الآن", "en": "Assistant is replying"},
    "problem.assistant_busy.detail": {
        "ar": "انتظر حتى ينتهي الرد الحالي في هذه المحادثة.",
        "en": "Wait for the current reply in this conversation to finish.",
    },
    "problem.nothing_to_answer.title": {"ar": "لا رسالة جديدة", "en": "Nothing to answer"},
    "problem.nothing_to_answer.detail": {
        "ar": "أرسل رسالة جديدة أولًا ثم اطلب الرد.",
        "en": "Send a new message before asking for a reply.",
    },
    "problem.action_already_decided.title": {"ar": "حُسم الطلب", "en": "Already decided"},
    "problem.action_already_decided.detail": {
        "ar": "أُكد هذا الطلب أو أُلغي من قبل.",
        "en": "This request was already confirmed or cancelled.",
    },
    "retake.blurry": {"ar": "الصورة غير واضحة. ثبّت الجوال وصوّر مرة أخرى.", "en": "The photo is blurry."},
    "retake.too_dark": {"ar": "الصورة مظلمة جدًا. صوّر في إضاءة أفضل.", "en": "The photo is too dark."},
    "retake.too_bright": {"ar": "الصورة ساطعة جدًا. تجنّب الشمس المباشرة.", "en": "The photo is too bright."},
    "retake.wrong_angle": {
        "ar": "الزاوية بعيدة عن الصورة المرجعية. طابق الإطار الشفاف وصوّر مرة أخرى.",
        "en": "The angle differs from the reference. Match the overlay and retake.",
    },
    "retake.lighting": {
        "ar": "قد يكون التغيير ظلًا. صوّر في وقت آخر من اليوم إن أمكن.",
        "en": "The change may be a shadow. Retake at another time of day if you can.",
    },
    "retake.unclear_change": {
        "ar": "التغيير غير واضح. اقترب قليلًا وصوّر مرة أخرى.",
        "en": "The change is unclear. Move closer and retake.",
    },
    "retake.unusable_wall": {
        "ar": "تعذر تحليل الجدار في هذه الصورة. صوّر الجدار كاملًا في إضاءة جيدة.",
        "en": "The wall could not be analysed in this photo. Photograph the whole wall in good light.",
    },
    "question.which_facade": {"ar": "أي واجهة صوّرت؟", "en": "Which facade did you photograph?"},
    "story.no_verified_source": {
        "ar": "ليس لدي مصدر موثّق عن هذا المعلم بعد.",
        "en": "I have no verified source for this landmark yet.",
    },
}


def translate(key: str, lang: str = "ar", **params: Any) -> str:
    entry = MESSAGES.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry["ar"]
    return text.format(**params) if params else text
