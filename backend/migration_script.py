#!/usr/bin/env python3
"""
Database Migration Script for Face Attendance System
This script migrates from the old database schema to the new production-ready schema.
"""

import sqlite3
import json
import numpy as np
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Migrate the database from old schema to new schema"""
    
    # Database paths
    old_db_path = "face_attendance.db"
    new_db_path = "face_attendance_new.db"
    
    logger.info("Starting database migration...")
    
    # Connect to old database
    old_conn = sqlite3.connect(old_db_path)
    old_cursor = old_conn.cursor()
    
    # Create new database with new schema
    new_conn = sqlite3.connect(new_db_path)
    new_cursor = new_conn.cursor()
    
    try:
        # Create new tables
        logger.info("Creating new database schema...")
        
        # Students table
        new_cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                roll_no VARCHAR(50) UNIQUE NOT NULL,
                branch VARCHAR(50),
                year INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Student embeddings table
        new_cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_embeddings (
                student_id INTEGER PRIMARY KEY,
                embedding BLOB NOT NULL,
                model_version VARCHAR(50) DEFAULT 'buffalo_l',
                quality_score FLOAT DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
        """)
        
        # Attendance log table
        new_cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                confidence FLOAT NOT NULL,
                camera_source VARCHAR(100),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
        """)
        
        # Create unique constraint separately
        new_cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS unique_daily_attendance 
            ON attendance_log(student_id, DATE(detected_at))
        """)
        
        # Create indexes
        new_cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_date ON attendance_log(student_id, DATE(detected_at))")
        new_cursor.execute("CREATE INDEX IF NOT EXISTS idx_roll_no ON students(roll_no)")
        
        # Migrate students data
        logger.info("Migrating students data...")
        
        # Get students from old database
        old_cursor.execute("SELECT id, name, roll_number, created_at FROM students")
        old_students = old_cursor.fetchall()
        
        for student in old_students:
            old_id, name, roll_number, created_at = student
            
            # Insert into new students table
            new_cursor.execute("""
                INSERT INTO students (student_id, name, roll_no, created_at)
                VALUES (?, ?, ?, ?)
            """, (old_id, name, roll_number, created_at))
            
            logger.info(f"Migrated student: {name} (ID: {old_id})")
        
        # Migrate embeddings data
        logger.info("Migrating embeddings data...")
        
        # Get embeddings from old database
        old_cursor.execute("SELECT id, embedding_vector, face_embedding, liveness_confidence_score FROM students WHERE embedding_vector IS NOT NULL OR face_embedding IS NOT NULL")
        old_embeddings = old_cursor.fetchall()
        
        for embedding_data in old_embeddings:
            old_id, embedding_vector, face_embedding, confidence = embedding_data
            
            # Use face_embedding if available, otherwise parse embedding_vector
            if face_embedding:
                embedding_blob = face_embedding
            elif embedding_vector:
                try:
                    # Parse JSON embedding vector
                    embedding_array = np.array(json.loads(embedding_vector), dtype=np.float32)
                    embedding_blob = embedding_array.tobytes()
                except Exception as e:
                    logger.warning(f"Failed to parse embedding for student {old_id}: {e}")
                    continue
            else:
                continue
            
            # Insert into new embeddings table
            new_cursor.execute("""
                INSERT INTO student_embeddings (student_id, embedding, quality_score)
                VALUES (?, ?, ?)
            """, (old_id, embedding_blob, confidence or 0.0))
            
            logger.info(f"Migrated embedding for student ID: {old_id}")
        
        # Migrate attendance data
        logger.info("Migrating attendance data...")
        
        # Get attendance from old database
        old_cursor.execute("SELECT id, student_id, timestamp, confidence_score, camera_location FROM attendance_log")
        old_attendance = old_cursor.fetchall()
        
        for attendance in old_attendance:
            old_id, student_id, timestamp, confidence, camera_location = attendance
            
            # Insert into new attendance log table
            new_cursor.execute("""
                INSERT INTO attendance_log (student_id, detected_at, confidence, camera_source)
                VALUES (?, ?, ?, ?)
            """, (student_id, timestamp, confidence or 0.0, camera_location))
            
            logger.info(f"Migrated attendance record for student ID: {student_id}")
        
        # Commit changes
        new_conn.commit()
        
        logger.info("Database migration completed successfully!")
        logger.info(f"New database saved as: {new_db_path}")
        
        # Print migration summary
        new_cursor.execute("SELECT COUNT(*) FROM students")
        student_count = new_cursor.fetchone()[0]
        
        new_cursor.execute("SELECT COUNT(*) FROM student_embeddings")
        embedding_count = new_cursor.fetchone()[0]
        
        new_cursor.execute("SELECT COUNT(*) FROM attendance_log")
        attendance_count = new_cursor.fetchone()[0]
        
        logger.info(f"Migration Summary:")
        logger.info(f"  Students migrated: {student_count}")
        logger.info(f"  Embeddings migrated: {embedding_count}")
        logger.info(f"  Attendance records migrated: {attendance_count}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        new_conn.rollback()
        raise
    finally:
        old_conn.close()
        new_conn.close()

if __name__ == "__main__":
    migrate_database()
