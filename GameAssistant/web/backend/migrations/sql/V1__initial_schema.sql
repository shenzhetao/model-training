-- V1__initial_schema.sql
-- Initial database schema for GameAssistant Platform
-- Created: 2026-06-22

-- Create database if not exists (for local development)
-- CREATE DATABASE IF NOT EXISTS gameassistant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- =====================================================
-- Table 1: users (用户表)
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'annotator',
    email VARCHAR(128) UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    INDEX idx_users_username (username),
    INDEX idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 2: images (图片元信息表)
-- =====================================================
CREATE TABLE IF NOT EXISTS images (
    id CHAR(36) PRIMARY KEY,
    filename VARCHAR(256) NOT NULL,
    original_filename VARCHAR(256) NOT NULL,
    file_path VARCHAR(512) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    md5_hash VARCHAR(32) NOT NULL,
    phash VARCHAR(64) NULL,
    source VARCHAR(16) NOT NULL DEFAULT 'upload',
    source_video_id CHAR(36) NULL,
    source_video_timestamp FLOAT NULL,
    uploaded_by CHAR(36) NULL,
    uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_images_md5 (md5_hash),
    INDEX idx_images_source (source),
    INDEX idx_images_uploaded_at (uploaded_at),
    INDEX idx_images_source_video (source_video_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 3: source_videos (源视频表)
-- =====================================================
CREATE TABLE IF NOT EXISTS source_videos (
    id CHAR(36) PRIMARY KEY,
    filename VARCHAR(256) NOT NULL,
    original_filename VARCHAR(256) NOT NULL,
    file_path VARCHAR(512) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    duration FLOAT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    fps FLOAT NOT NULL,
    uploaded_by CHAR(36) NULL,
    uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_source_videos_uploaded_at (uploaded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 4: video_extraction_tasks (视频抽帧任务表)
-- =====================================================
CREATE TABLE IF NOT EXISTS video_extraction_tasks (
    id CHAR(36) PRIMARY KEY,
    video_id CHAR(36) NOT NULL,
    strategy VARCHAR(32) NOT NULL,
    interval_seconds FLOAT NULL,
    frame_count INT NULL,
    scene_threshold FLOAT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    total_frames INT NULL,
    extracted_frames INT NULL DEFAULT 0,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT NULL,
    INDEX idx_video_extraction_video_id (video_id),
    INDEX idx_video_extraction_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 5: classes (类别表)
-- =====================================================
CREATE TABLE IF NOT EXISTS classes (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    color VARCHAR(7) NOT NULL DEFAULT '#3B82F6',
    short_key VARCHAR(8) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    yolo_class_id INT NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_classes_yolo_class_id (yolo_class_id),
    INDEX idx_classes_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 6: annotations (标注记录表)
-- =====================================================
CREATE TABLE IF NOT EXISTS annotations (
    id CHAR(36) PRIMARY KEY,
    image_id CHAR(36) NOT NULL,
    class_id CHAR(36) NOT NULL,
    bbox_x FLOAT NOT NULL,
    bbox_y FLOAT NOT NULL,
    bbox_width FLOAT NOT NULL,
    bbox_height FLOAT NOT NULL,
    conf FLOAT NULL,
    is_auto_annotated TINYINT(1) NOT NULL DEFAULT 0,
    annotated_by CHAR(36) NULL,
    annotated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_annotations_image_id (image_id),
    INDEX idx_annotations_class_id (class_id),
    INDEX idx_annotations_image_class (image_id, class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 7: annotation_projects (标注项目表)
-- =====================================================
CREATE TABLE IF NOT EXISTS annotation_projects (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    class_ids JSON NOT NULL,
    total_images INT NOT NULL DEFAULT 0,
    annotated_images INT NOT NULL DEFAULT 0,
    reviewed_images INT NOT NULL DEFAULT 0,
    assigned_to CHAR(36) NULL,
    reviewed_by CHAR(36) NULL,
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    INDEX idx_annotation_projects_status (status),
    INDEX idx_annotation_projects_assigned_to (assigned_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 8: annotation_project_images (标注项目-图片关联表)
-- =====================================================
CREATE TABLE IF NOT EXISTS annotation_project_images (
    id CHAR(36) PRIMARY KEY,
    annotation_project_id CHAR(36) NOT NULL,
    image_id CHAR(36) NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_annotation_project_image (annotation_project_id, image_id),
    INDEX idx_annotation_project_images_project_id (annotation_project_id),
    INDEX idx_annotation_project_images_image_id (image_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 9: annotation_reviews (标注审核记录表)
-- =====================================================
CREATE TABLE IF NOT EXISTS annotation_reviews (
    id CHAR(36) PRIMARY KEY,
    annotation_project_id CHAR(36) NOT NULL,
    image_id CHAR(36) NOT NULL,
    review_status VARCHAR(32) NOT NULL,
    reviewer_id CHAR(36) NULL,
    rejection_reason TEXT NULL,
    reviewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_annotation_review (annotation_project_id, image_id),
    INDEX idx_annotation_reviews_project (annotation_project_id),
    INDEX idx_annotation_reviews_image (image_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 10: datasets (数据集表)
-- =====================================================
CREATE TABLE IF NOT EXISTS datasets (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_datasets_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 11: dataset_versions (数据集版本表)
-- =====================================================
CREATE TABLE IF NOT EXISTS dataset_versions (
    id CHAR(36) PRIMARY KEY,
    dataset_id CHAR(36) NOT NULL,
    version_name VARCHAR(128) NOT NULL,
    version_number INT NOT NULL,
    train_ratio FLOAT NOT NULL DEFAULT 0.9,
    val_ratio FLOAT NOT NULL DEFAULT 0.1,
    test_ratio FLOAT NOT NULL DEFAULT 0.0,
    random_seed INT NOT NULL DEFAULT 42,
    image_count INT NOT NULL DEFAULT 0,
    annotated_count INT NOT NULL DEFAULT 0,
    class_ids JSON NOT NULL,
    yolo_dataset_path VARCHAR(512) NULL,
    dataset_yaml_content TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'preparing',
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_dataset_version_name (dataset_id, version_name),
    UNIQUE KEY uk_dataset_version_number (dataset_id, version_number),
    INDEX idx_dataset_versions_dataset_id (dataset_id),
    INDEX idx_dataset_versions_status (status),
    INDEX idx_dataset_versions_created_at (created_at),
    CHECK (train_ratio + val_ratio + test_ratio <= 1.0 AND train_ratio >= 0 AND val_ratio >= 0 AND test_ratio >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 12: dataset_version_images (数据集版本-图片关联表)
-- =====================================================
CREATE TABLE IF NOT EXISTS dataset_version_images (
    id CHAR(36) PRIMARY KEY,
    dataset_version_id CHAR(36) NOT NULL,
    image_id CHAR(36) NOT NULL,
    split VARCHAR(16) NOT NULL,
    added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_dataset_version_image (dataset_version_id, image_id),
    INDEX idx_dataset_version_images_version_id (dataset_version_id),
    INDEX idx_dataset_version_images_split (split),
    INDEX idx_dataset_version_images_image_id (image_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 13: models (模型表)
-- =====================================================
CREATE TABLE IF NOT EXISTS models (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    architecture VARCHAR(32) NOT NULL,
    task_type VARCHAR(32) NOT NULL DEFAULT 'detect',
    file_path VARCHAR(512) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    format VARCHAR(16) NOT NULL DEFAULT 'pt',
    dataset_version_id CHAR(36) NULL,
    class_ids JSON NOT NULL,
    yolo_class_names JSON NOT NULL,
    epochs INT NULL,
    batch_size INT NULL,
    img_size INT NULL,
    map50 FLOAT NULL,
    map50_95 FLOAT NULL,
    train_loss FLOAT NULL,
    val_loss FLOAT NULL,
    trained_at DATETIME NULL,
    training_job_id CHAR(36) NULL,
    tags JSON NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    uploaded_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_models_architecture (architecture),
    INDEX idx_models_dataset_version_id (dataset_version_id),
    INDEX idx_models_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 14: training_jobs (训练任务表)
-- =====================================================
CREATE TABLE IF NOT EXISTS training_jobs (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    dataset_version_id CHAR(36) NOT NULL,
    base_model_architecture VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    epochs INT NOT NULL DEFAULT 50,
    batch_size INT NOT NULL DEFAULT 8,
    img_size INT NOT NULL DEFAULT 640,
    lr0 FLOAT NOT NULL DEFAULT 0.01,
    lrf FLOAT NOT NULL DEFAULT 0.01,
    weight_decay FLOAT NOT NULL DEFAULT 0.0005,
    momentum FLOAT NOT NULL DEFAULT 0.937,
    patience INT NOT NULL DEFAULT 15,
    mosaic FLOAT NOT NULL DEFAULT 1.0,
    mixup FLOAT NOT NULL DEFAULT 0.0,
    hsv_h FLOAT NOT NULL DEFAULT 0.015,
    hsv_s FLOAT NOT NULL DEFAULT 0.7,
    hsv_v FLOAT NOT NULL DEFAULT 0.4,
    flip_lr FLOAT NOT NULL DEFAULT 0.5,
    resume_from CHAR(36) NULL,
    best_model_id CHAR(36) NULL,
    process_id INT NULL,
    log_output LONGTEXT NULL,
    log_summary JSON NULL,
    current_epoch INT NULL,
    gpu_device VARCHAR(16) NULL,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT NULL,
    INDEX idx_training_jobs_dataset_version_id (dataset_version_id),
    INDEX idx_training_jobs_status (status),
    INDEX idx_training_jobs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 15: training_logs (训练 epoch 日志表)
-- =====================================================
CREATE TABLE IF NOT EXISTS training_logs (
    id CHAR(36) PRIMARY KEY,
    training_job_id CHAR(36) NOT NULL,
    epoch INT NOT NULL,
    train_box_loss FLOAT NULL,
    train_cls_loss FLOAT NULL,
    train_dfl_loss FLOAT NULL,
    val_box_loss FLOAT NULL,
    val_cls_loss FLOAT NULL,
    val_dfl_loss FLOAT NULL,
    precision FLOAT NULL,
    recall FLOAT NULL,
    map50 FLOAT NULL,
    map50_95 FLOAT NULL,
    lr FLOAT NULL,
    gpu_memory_mb INT NULL,
    epoch_duration_sec INT NULL,
    logged_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_training_log_epoch (training_job_id, epoch),
    INDEX idx_training_logs_job_id (training_job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 16: device_profiles (设备配置表)
-- =====================================================
CREATE TABLE IF NOT EXISTS device_profiles (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    device_id VARCHAR(128) NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    dpi INT NULL,
    reference_width INT NOT NULL,
    reference_height INT NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    is_default TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_device_profiles_device_id (device_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 17: templates (模板表)
-- =====================================================
CREATE TABLE IF NOT EXISTS templates (
    id CHAR(36) PRIMARY KEY,
    device_profile_id CHAR(36) NULL,
    class_name VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    file_path VARCHAR(512) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    roi_x INT NULL,
    roi_y INT NULL,
    roi_width INT NULL,
    roi_height INT NULL,
    match_threshold FLOAT NOT NULL DEFAULT 0.8,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    trained_at DATETIME NULL,
    uploaded_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_templates_class_name (class_name),
    INDEX idx_templates_device_profile_id (device_profile_id),
    INDEX idx_templates_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 18: template_classes (模板类别表)
-- =====================================================
CREATE TABLE IF NOT EXISTS template_classes (
    id CHAR(36) PRIMARY KEY,
    class_name VARCHAR(64) NOT NULL UNIQUE,
    display_name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    default_threshold FLOAT NOT NULL DEFAULT 0.8,
    icon VARCHAR(64) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 19: inference_logs (推理日志表)
-- =====================================================
CREATE TABLE IF NOT EXISTS inference_logs (
    id CHAR(36) PRIMARY KEY,
    image_id CHAR(36) NULL,
    model_id CHAR(36) NOT NULL,
    template_ids JSON NULL,
    detection_mode VARCHAR(32) NOT NULL,
    conf_threshold FLOAT NOT NULL,
    input_width INT NOT NULL,
    input_height INT NOT NULL,
    screenshot_latency_ms FLOAT NULL,
    template_latency_ms FLOAT NULL,
    yolo_latency_ms FLOAT NULL,
    total_latency_ms FLOAT NOT NULL,
    results JSON NOT NULL,
    result_count INT NOT NULL,
    device_profile_id CHAR(36) NULL,
    inference_type VARCHAR(16) NOT NULL DEFAULT 'single',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_inference_logs_model_id (model_id),
    INDEX idx_inference_logs_created_at (created_at),
    INDEX idx_inference_logs_detection_mode (detection_mode)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 20: operation_logs (操作日志表)
-- =====================================================
CREATE TABLE IF NOT EXISTS operation_logs (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NULL,
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(32) NOT NULL,
    resource_id CHAR(36) NULL,
    details JSON NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(256) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operation_logs_user_id (user_id),
    INDEX idx_operation_logs_action (action),
    INDEX idx_operation_logs_resource (resource_type, resource_id),
    INDEX idx_operation_logs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Table 21: notifications (通知表)
-- =====================================================
CREATE TABLE IF NOT EXISTS notifications (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    type VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    message TEXT NOT NULL,
    resource_type VARCHAR(32) NULL,
    resource_id CHAR(36) NULL,
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notifications_user_id (user_id),
    INDEX idx_notifications_is_read (is_read),
    INDEX idx_notifications_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- Insert default admin user (password: admin123)
-- bcrypt hash of 'admin123'
-- =====================================================
INSERT INTO users (id, username, password_hash, role, email, is_active)
VALUES (
    UUID(),
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.dU.iGQv0Zj0Cma',
    'admin',
    'admin@gameassistant.local',
    1
);

-- =====================================================
-- Insert default template classes
-- =====================================================
INSERT INTO template_classes (id, class_name, display_name, description, sort_order) VALUES
(UUID(), 'btn_attack', '攻击按钮', '右下角攻击键', 1),
(UUID(), 'btn_skill', '技能按钮', '8个技能槽', 2),
(UUID(), 'hp_bar_player', '角色血条', '角色血量条', 3),
(UUID(), 'dialog_next', '对话箭头', 'NPC对话下一步箭头', 4);
