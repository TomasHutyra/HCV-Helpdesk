from django.contrib import admin
from .models import Ticket, Comment, TimeLog, Area, TicketAttachment


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_unknown', 'created_at')
    list_filter = ('is_unknown',)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('author', 'created_at')


class TimeLogInline(admin.TabularInline):
    model = TimeLog
    extra = 0
    readonly_fields = ('user', 'created_at')


class AttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ('original_name', 'uploaded_by', 'created_at')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('pk', 'title', 'type', 'status', 'priority', 'company', 'requester', 'resolver', 'created_at')
    list_filter = ('status', 'type', 'priority', 'area', 'company')
    search_fields = ('title', 'description')
    readonly_fields = ('status', 'created_at', 'updated_at', 'resolved_at')
    inlines = [CommentInline, TimeLogInline, AttachmentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'ticket', 'author', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    list_display = ('pk', 'ticket', 'user', 'hours', 'note', 'created_at')
    readonly_fields = ('created_at',)
