from django.urls import path

from sites.admin_api.newsletter_views import (
    NewsletterCombinedView,
    NewsletterExportView,
    NewsletterMergeMembersView,
    NewsletterSubscriberDestroyView,
    NewsletterSubscriberUnsubscribeView,
    NewsletterSubscribersListView,
)

urlpatterns = [
    path('merge-members', NewsletterMergeMembersView.as_view()),
    path('merge-members/', NewsletterMergeMembersView.as_view()),
    path('combined', NewsletterCombinedView.as_view()),
    path('combined/', NewsletterCombinedView.as_view()),
    path('export', NewsletterExportView.as_view()),
    path('export/', NewsletterExportView.as_view()),
    path(
        'subscribers/<int:subscriber_id>/unsubscribe',
        NewsletterSubscriberUnsubscribeView.as_view(),
    ),
    path(
        'subscribers/<int:subscriber_id>/unsubscribe/',
        NewsletterSubscriberUnsubscribeView.as_view(),
    ),
    path('subscribers/<int:subscriber_id>', NewsletterSubscriberDestroyView.as_view()),
    path('subscribers/<int:subscriber_id>/', NewsletterSubscriberDestroyView.as_view()),
    path('subscribers', NewsletterSubscribersListView.as_view()),
    path('subscribers/', NewsletterSubscribersListView.as_view()),
]
