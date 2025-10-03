# Model Test Coverage
1. **OTP Model Tests**:
   - `test_generate_otp`: Verifies the OTP generation logic.
   - `test_hash_otp`: Ensures the OTP hashing function works correctly.
   - `test_create_otp`: Tests the 

create_otp

 function for creating an OTP instance.
   - `test_otp_is_valid`: Tests the 

is_valid

 method under various conditions (expired, used, max attempts).
   - `test_otp_verify`: Tests the 

verify

 method for correct and incorrect OTPs.

2. **User Model Tests**:
   - `test_create_user`: Verifies the creation of a regular user.
   - `test_create_superuser`: Verifies the creation of a superuser.
   - `test_user_str`: Tests the string representation of the user.
   - `test_user_email_otp_relationship`: Ensures the relationship between 

User and OTP works as expected.


---

### Serializers

#### **Testing User Defaults**
- `test_user_defaults`: Verifies that the default values for fields like `balance`, `transfer_allowed`, `transfer_limit`, 

is_active

, `email_verified`, and `mfa_enabled` are correctly set when a user is created.

#### **Testing 

UserSerializer

**
- `test_user_serializer`: Ensures that the 

UserSerializer

 correctly serializes the 

User

 model fields.
- `test_user_serializer_update`: Tests the 

update

 method of the 

UserSerializer

 to ensure it updates the 

User

 instance correctly. 

- Test to make sure critical params like balance, email, phone_number and mfa_enabled can't be updated using this serializer.

#### **Testing 

EmailOTPSerializer

**
- `test_email_otp_serializer_valid`: Verifies that the 

EmailOTPSerializer

 validates correct data.
- `test_email_otp_serializer_invalid`: Ensures that invalid data (e.g., invalid email or code) is caught by the serializer.

#### **Testing 

ResendOTPSerializer

**
- `test_resend_otp_serializer_valid`: Verifies that the 

ResendOTPSerializer

 validates correct data (valid UUID).
- `test_resend_otp_serializer_invalid`: Ensures that invalid data (e.g., invalid UUID) is caught by the serializer.

---
