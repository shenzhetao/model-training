-- V2__add_user_password_changed.sql
-- Add is_password_changed field to users table
-- Created: 2026-06-23

ALTER TABLE users
ADD COLUMN is_password_changed TINYINT(1) NOT NULL DEFAULT 0
AFTER is_active;
