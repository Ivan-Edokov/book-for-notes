import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)

TEXT_POST_CREATED = 'Тестовый пост из формы создания'
TEXT_POST_EDITED = 'Измененный текст поста'


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='testslug',
            description='Тестовое описание группы',
        )
        cls.group_edit = Group.objects.create(
            title='Название группы после редактирования поста',
            slug='testslug_edit',
            description='Тестовое описание группы',
        )
        uploaded = SimpleUploadedFile(
            name='small_gif',
            content=SMALL_GIF,
            content_type="image/gif",
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.autoriset_client = Client()
        self.autoriset_client.force_login(PostCreateFormTests.user)

    def test_create_form(self):
        """Валидная форма create создает запись в Post."""
        post_count = Post.objects.count()
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_data = {
            'text': TEXT_POST_CREATED,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.autoriset_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse('posts:profile',
                              kwargs={'username': PostCreateFormTests.user})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=TEXT_POST_CREATED,
                group=self.group.id,
                image=f'posts/{uploaded.name}'
            ).exists()
        )

    def test_create_post_form(self):
        """Валидная форма редактирования поста изменяет в БД"""
        post_count = Post.objects.count()
        uploaded = SimpleUploadedFile(
            name='small_edit.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_data = {
            'text': TEXT_POST_EDITED,
            'group': self.group_edit.id,
            'image': uploaded,
        }
        response = self.autoriset_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostCreateFormTests.post.id}
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': PostCreateFormTests.post.id}
            )
        )
        self.assertTrue(
            Post.objects.filter(
                id=PostCreateFormTests.post.id,
                text=TEXT_POST_EDITED,
                group=self.group_edit,
                image=f'posts/{uploaded.name}'
            ).exists()
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_comments_add_only_authorized_user(self):
        """
        Комментировать посты могут оставлять
        только авторизованные пользователи
        """
        comment_count = Comment.objects.filter(
            post=PostCreateFormTests.post
        ).count()
        comment_text = f'{self.user} - автор комментария к посту'
        form_data = {'text': comment_text}
        response = self.autoriset_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostCreateFormTests.post.id}
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': PostCreateFormTests.post.id}
            )
        )
        self.assertEqual(Comment.objects.filter(
            post=PostCreateFormTests.post).count(),
            comment_count + 1
        )
        self.assertTrue(
            Comment.objects.filter(
                text=comment_text,
                post=PostCreateFormTests.post
            ).exists()
        )

    def test_comments_not_add_unauthorized_user(self):
        """
        Неавторизованный пользователь не может комментировать посты
        """
        comment_count = Comment.objects.filter(
            post=PostCreateFormTests.post
        ).count()
        comment_text = 'Комментарий к посту от неавторизованного пользователя'
        form_data = {'text': comment_text}
        response = self.client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostCreateFormTests.post.id}
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('users:login')
            + '?next='
            + reverse(
                'posts:add_comment',
                kwargs={'post_id': PostCreateFormTests.post.id})
        )
        self.assertEqual(Comment.objects.filter(
            post=PostCreateFormTests.post).count(),
            comment_count
        )
        self.assertFalse(
            Comment.objects.filter(
                text=comment_text,
                post=PostCreateFormTests.post
            ).exists()
        )
