from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Company, UserRole


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserRoleInline]
    list_display = ('username', 'email', 'get_full_name', 'company', 'is_active')
    list_filter = ('is_active', 'user_roles__role', 'company')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('HCV Helpdesk', {'fields': ('company', 'language')}),
    )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
