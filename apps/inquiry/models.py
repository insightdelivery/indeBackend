from django.db import models


class Inquiry(models.Model):
    STATUS_CHOICES = (
        ("waiting", "접수"),
        ("answered", "답변완료"),
    )

    user = models.ForeignKey(
        "public_api.PublicMemberShip",
        on_delete=models.CASCADE,
        related_name="inquiries",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    answer = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="waiting"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "1:1 문의"
        verbose_name_plural = "1:1 문의"

    def __str__(self):
        return self.title[:50]
