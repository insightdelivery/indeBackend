from django.db import models


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "자주 묻는 질문"
        verbose_name_plural = "자주 묻는 질문"

    def __str__(self):
        return self.question[:50]
