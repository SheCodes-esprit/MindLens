from django.db import models
from django.core.exceptions import ValidationError
from users.models import User


class Tag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Entry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    feeling = models.CharField(max_length=50, blank=True, null=True)
    tag = models.ForeignKey(
        Tag, on_delete=models.SET_NULL, null=True, blank=True, related_name="entries"
    )

    def clean(self):
        if not self.content.strip():
            raise ValidationError({"content": "Content cannot be empty."})

    def save(self, *args, **kwargs):
        if not self.title or not self.title.strip():
            self.title = "Untitled"

        if not self.tag:
            untagged_tag, _ = Tag.objects.get_or_create(
                user=self.user, name="Untagged"
            )
            self.tag = untagged_tag

        self.full_clean() 
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class TextEntryInsight(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="insights")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    summary = models.TextField(blank=True, null=True)
    sentiment = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Insight for '{self.entry.title}' by {self.user.username}"