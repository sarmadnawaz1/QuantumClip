#!/usr/bin/env python3
"""
Script to reset a user's password in the Shazi Video Generator database
Usage: python3 reset_password.py
"""

import sqlite3
import sys
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def list_users():
    """List all users in the database."""
    conn = sqlite3.connect('shazi_videogen.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, email, username, is_active FROM users ORDER BY id')
    users = cursor.fetchall()
    conn.close()
    
    print("\n" + "="*70)
    print("📋 CURRENT USERS IN DATABASE")
    print("="*70)
    for user in users:
        status = "✅ Active" if user[3] else "❌ Inactive"
        print(f"ID: {user[0]:2d} | Email: {user[1]:30s} | Username: {user[2]:15s} | {status}")
    print("="*70 + "\n")
    return users

def reset_password(email: str, new_password: str):
    """Reset password for a user."""
    conn = sqlite3.connect('shazi_videogen.db')
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute('SELECT id, email, username FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    
    if not user:
        print(f"❌ Error: No user found with email: {email}")
        conn.close()
        return False
    
    # Hash the new password
    hashed_password = get_password_hash(new_password)
    
    # Update the password
    cursor.execute('UPDATE users SET hashed_password = ? WHERE email = ?', (hashed_password, email))
    conn.commit()
    conn.close()
    
    print(f"\n✅ Password successfully reset for:")
    print(f"   Email: {user[1]}")
    print(f"   Username: {user[2]}")
    print(f"   New Password: {new_password}")
    print(f"\n🔐 You can now log in with this email and password!\n")
    return True

def main():
    """Main function."""
    print("\n" + "="*70)
    print("🔐 SHAZI VIDEO GENERATOR - PASSWORD RESET UTILITY")
    print("="*70)
    
    # List all users
    users = list_users()
    
    if not users:
        print("❌ No users found in database.")
        return
    
    # Get user input
    print("Enter the email address of the user whose password you want to reset:")
    email = input("Email: ").strip()
    
    print("\nEnter the new password:")
    new_password = input("New Password: ").strip()
    
    if len(new_password) < 6:
        print("\n❌ Error: Password must be at least 6 characters long.")
        return
    
    # Confirm
    print(f"\n⚠️  Are you sure you want to reset the password for '{email}'? (yes/no)")
    confirm = input("Confirm: ").strip().lower()
    
    if confirm in ['yes', 'y']:
        reset_password(email, new_password)
    else:
        print("\n❌ Password reset cancelled.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
