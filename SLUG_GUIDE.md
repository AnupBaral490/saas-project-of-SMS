# Understanding Slug in SaaS Signup

## What is a Slug?

A **slug** is a URL-friendly identifier created from your organization name. It's used to create the subdomain where your school's system will be accessible.

### Example
**Organization Name:** `Sos Herman Gmeiner School`  
**Auto-Generated Slug:** `sos-herman-gmeiner-school`  
**Your Access URL:** `sos-herman-gmeiner-school.localhost:8000` (development) or `sos-herman-gmeiner-school.yourdomain.com` (production)

## Slug Rules

A slug is created by following these rules:
1. **Lowercase** - All letters are converted to lowercase
2. **No spaces** - Spaces are replaced with hyphens (-)
3. **No special characters** - Accents, symbols, and punctuation are removed
4. **URL-safe** - Only contains letters, numbers, and hyphens

## Examples

| Organization Name | Generated Slug |
|---|---|
| Sos Herman Gmeiner School | sos-herman-gmeiner-school |
| St. Mary's Academy | st-marys-academy |
| ABC Public School (2024) | abc-public-school-2024 |
| Lycée Français | lycee-francais |
| School #1 | school-1 |

## How It Works in Our System

### Step 1: Auto-Generation
When you type your organization name in the form, the slug is **automatically generated** in real-time:

1. Type: `Sos Herman Gmeiner School`
2. System generates: `sos-herman-gmeiner-school`
3. Shows your URL: `sos-herman-gmeiner-school.localhost:8000`

### Step 2: Uniqueness Check
As you type, the system checks if your slug is already taken:
- ✅ **Green checkmark** = Subdomain available
- ❌ **Red X** = Subdomain already in use (choose a different name)

### Step 3: Confirmation
When you submit the form, the system verifies one more time that your slug is unique before creating your account.

## What if My Slug is Taken?

If `sos-herman-gmeiner-school` is already taken, try:
- Add a location: `sos-herman-gmeiner-school-delhi`
- Add a year: `sos-herman-gmeiner-school-2024`
- Abbreviate: `shgs-delhi`
- Simplify: `shgs-india`

## Important Notes

✅ **Do:**
- Choose a slug that clearly identifies your organization
- Make it memorable and easy to spell
- Keep it short but descriptive
- Avoid overly generic names

❌ **Don't:**
- Manually edit the slug field (it's read-only)
- Use spaces or special characters
- Make it too long (max 63 characters)
- Use unprofessional names

## Production Domains

In development: `yourschool.localhost:8000`

In production, your domain would be:
- **Subdomain style:** `yourschool.studentmanagementsystem.com`
- **Custom domain:** `yourschool.edu.in` (if you own the domain)

The slug remains the same in both cases - it's the subdomain portion of your school's unique URL.

## Need to Change It Later?

Once your account is created, only administrators can request slug/subdomain changes. This is intentional to prevent users from accidentally breaking their school's access URL.

---

**FAQ:**

**Q: Can I change my slug after signup?**  
A: Contact support. We can help change it with proper permissions, but be aware existing links/bookmarks will break.

**Q: What if I want a completely custom domain?**  
A: Enterprise plan customers can set up custom domains. Contact sales.

**Q: Can slugs have numbers?**  
A: Yes! Example: `school123` or `abc-school-2024` are valid.

**Q: Is my slug case-sensitive?**  
A: No, all slugs are lowercase. `MySchool` and `myschool` are the same.
