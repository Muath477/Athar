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
    "problem.account_disabled.title": {"ar": "الحساب موقوف", "en": "Account disabled"},
    "problem.account_disabled.detail": {
        "ar": "أوقف مسؤول النظام هذا الحساب. تواصل معه لإعادة تفعيله.",
        "en": "An administrator disabled this account. Ask them to reactivate it.",
    },
    "problem.password_change_required.title": {"ar": "غيّر كلمة المرور", "en": "Password change required"},
    "problem.password_change_required.detail": {
        "ar": "عيّن كلمة مرور جديدة قبل المتابعة.",
        "en": "Set a new password before you continue.",
    },
    "problem.weak_password.title": {"ar": "كلمة المرور قصيرة", "en": "Password too short"},
    "problem.weak_password.detail": {
        "ar": "استخدم {min_length} حرفًا على الأقل.",
        "en": "Use at least {min_length} characters.",
    },
    "problem.password_unchanged.title": {"ar": "كلمة المرور لم تتغير", "en": "Password unchanged"},
    "problem.password_unchanged.detail": {
        "ar": "اختر كلمة مرور مختلفة عن الحالية.",
        "en": "Choose a password different from the current one.",
    },
    "problem.user_exists.title": {"ar": "الحساب موجود", "en": "User exists"},
    "problem.user_exists.detail": {
        "ar": "يوجد حساب بهذا البريد.",
        "en": "An account with this email already exists.",
    },
    "problem.own_account.title": {"ar": "لا يمكن تعديل حسابك", "en": "Cannot change your own account"},
    "problem.own_account.detail": {
        "ar": "لا يغيّر المسؤول دوره ولا يوقف حسابه بنفسه. اطلب ذلك من مسؤول آخر.",
        "en": "Administrators cannot change their own role or disable themselves. Ask another administrator.",
    },
    "problem.unknown_site.title": {"ar": "موقع غير معروف", "en": "Unknown site"},
    "problem.unknown_site.detail": {
        "ar": "أحد المواقع المختارة غير مسجل.",
        "en": "One of the selected sites is not registered.",
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
    "problem.model_version_exists.title": {"ar": "الإصدار مسجل", "en": "Model version exists"},
    "problem.model_version_exists.detail": {
        "ar": "هذا الإصدار من النموذج مسجل من قبل. اختر رقم إصدار جديدًا.",
        "en": "This model version is already registered. Choose a new version number.",
    },
    "problem.model_status_unchanged.title": {"ar": "لا يمكن تغيير الحالة", "en": "Status cannot change"},
    "problem.model_status_unchanged.detail": {
        "ar": "حالة النموذج الحالية لا تسمح بهذا الإجراء.",
        "en": "The model's current status does not allow this action.",
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
    "problem.heic_unsupported.title": {"ar": "صيغة HEIC غير مدعومة", "en": "HEIC is not supported"},
    "problem.heic_unsupported.detail": {
        "ar": "لا يقرأ الخادم صور HEIC بعد ({file_name}). صدّرها بصيغة JPEG أو غيّر إعداد كاميرا الجوال.",
        "en": "This server cannot read HEIC photos yet ({file_name}). Export them as JPEG.",
    },
    "problem.batch_size.title": {"ar": "عدد الصور غير مقبول", "en": "Wrong number of photos"},
    "problem.batch_size.detail": {
        "ar": "أرسل من صورة واحدة إلى {max_files} صورة في الدفعة.",
        "en": "Send between 1 and {max_files} photos per batch.",
    },
    "problem.facade_not_in_site.title": {"ar": "الواجهة لا تتبع الموقع", "en": "Facade is not in this site"},
    "problem.facade_not_in_site.detail": {
        "ar": "اختر واجهة من الموقع نفسه.",
        "en": "Pick a facade that belongs to the chosen site.",
    },
    "problem.device_site_required.title": {"ar": "الموقع مطلوب", "en": "Site required"},
    "problem.device_site_required.detail": {
        "ar": "الكاميرا الثابتة تحتاج موقعًا تراقبه.",
        "en": "A fixed camera needs the site it watches.",
    },
    "problem.invalid_camera_url.title": {"ar": "رابط الكاميرا غير مقبول", "en": "Camera URL rejected"},
    "problem.invalid_camera_url.detail": {
        "ar": "استخدم رابط http أو https للقطة (أو rtsp للبث) دون كلمة مرور داخل الرابط.",
        "en": "Use an http(s) snapshot URL (or rtsp stream) with no password inside the URL.",
    },
    "problem.device_has_no_source.title": {"ar": "لا رابط للالتقاط", "en": "Nothing to capture from"},
    "problem.device_has_no_source.detail": {
        "ar": "أضف رابط لقطة أو بث لهذا الجهاز أولًا.",
        "en": "Add a snapshot or stream URL to this device first.",
    },
    "problem.job_not_retryable.title": {"ar": "لا يمكن إعادة المحاولة", "en": "Cannot retry"},
    "problem.job_not_retryable.detail": {
        "ar": "تُعاد المحاولة للصور المتعثرة المحفوظة فقط.",
        "en": "Only failed jobs with a stored photo can be retried.",
    },
    "problem.ingest_failed.title": {"ar": "تعذر تحليل الصورة", "en": "Photo could not be analysed"},
    "problem.ingest_failed.detail": {
        "ar": "تعذر تحليل الصورة بعد عدة محاولات. أعد المحاولة لاحقًا.",
        "en": "The photo could not be analysed after several attempts. Retry later.",
    },
    "camera.invalid_url": {"ar": "رابط الكاميرا غير مقبول.", "en": "The camera URL is not accepted."},
    "camera.unresolvable": {"ar": "تعذر العثور على عنوان الكاميرا.", "en": "The camera host was not found."},
    "camera.blocked_address": {
        "ar": "عنوان الكاميرا داخلي. أضفه إلى SADU_CAMERA_ALLOWED_HOSTS إن كانت الكاميرا على شبكة الموقع.",
        "en": "The camera address is internal. Allow it in SADU_CAMERA_ALLOWED_HOSTS if it is on site.",
    },
    "camera.timeout": {
        "ar": "لم تستجب الكاميرا في الوقت المحدد.",
        "en": "The camera did not answer in time.",
    },
    "camera.connection": {"ar": "تعذر الاتصال بالكاميرا.", "en": "Could not connect to the camera."},
    "camera.http_status": {
        "ar": "ردّت الكاميرا بالرمز {status}.",
        "en": "The camera answered with status {status}.",
    },
    "camera.not_image": {"ar": "لم ترسل الكاميرا صورة.", "en": "The camera did not send an image."},
    "camera.too_large": {
        "ar": "لقطة الكاميرا أكبر من الحد المسموح.",
        "en": "The snapshot is larger than allowed.",
    },
    "camera.rtsp_unavailable": {
        "ar": "التقاط البث RTSP يحتاج ffmpeg على الخادم.",
        "en": "RTSP capture needs ffmpeg on the server.",
    },
    "camera.no_source": {"ar": "لا رابط لقطة لهذا الجهاز.", "en": "This device has no snapshot URL."},
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
