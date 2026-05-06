from django import forms
from .models import Post, Comment, UserProfile, PropertyListing, Message


class PostForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control border-0 shadow-none',
            'placeholder': "What's on your mind? Share tips, ask questions, or post a listing...",
        }),
        max_length=2000,
    )
    post_type = forms.ChoiceField(
        choices=Post.POST_TYPES,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
    )

    class Meta:
        model = Post
        fields = ['content', 'post_type', 'image']


class CommentForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control border-0 shadow-none',
            'placeholder': 'Write a comment...',
        }),
        max_length=1000,
    )

    class Meta:
        model = Comment
        fields = ['content']


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        max_length=30, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = UserProfile
        fields = ['role', 'avatar', 'bio', 'location', 'phone', 'website']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, Country'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 234 567 8900'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
        }


class ListingForm(forms.ModelForm):
    class Meta:
        model = PropertyListing
        fields = [
            'title', 'description', 'listing_type', 'property_type',
            'price', 'location', 'bedrooms', 'bathrooms', 'area_sqm', 'image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Modern 2BR Apartment in City Center'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'listing_type': forms.Select(attrs={'class': 'form-select'}),
            'property_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full address or area'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'area_sqm': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class MessageForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control rounded-pill border-0 bg-light',
            'placeholder': 'Type a message...',
            'autocomplete': 'off',
        }),
        max_length=2000,
    )

    class Meta:
        model = Message
        fields = ['content']