from django.shortcuts import render, get_object_or_404
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from django.views.generic import ListView
from django.db.models import Count
from .forms import EmailPostForm, CommentForm
from taggit.models import Tag
# Create your views here.


class PostListView(ListView):
	queryset = Post.published.all()
	context_object_name = 'posts'
	paginate_by = 3
	template_name = 'blog/post/list.html'


def post_list(request, tag_slug=None):
	object_list = Post.published.all()
	tag = None

	if tag_slug:
		tag = get_object_or_404(Tag, slug=tag_slug)
		object_list = object_list.filter(tags__in=[tag])


#	posts = Post.published.all()
	paginator = Paginator(Post.objects.all()[:3], 3)
	page = request.GET.get('page')
	try:
		posts = paginator.page(page)
	except PageNotAnInteger:
		posts = paginator.page(1)
	except EmptyPage:
		posts = paginator.page(paginator.num_pages)

	return render(request,
				'blog/post/list.html',
				{'page': page,
				'posts': posts,
				'tag': tag})

def post_detail(request, year, month, day, post):
	post = get_object_or_404(Post, slug=post,
									status='published',
									publish__year=year,
									publish__month=month,
									publish__day=day)
	# list of avtive comments for this post
	comments = post.comments.filter(active=True)
	new_comment = None

	if request.method == 'POST':
		# A comment was posted
		comment_form = CommentForm(data=request.POST)
		if comment_form.is_valid():
			# create comment object but don't save to database yet
			new_comment = comment_form.save(commit=False)
			# Assign the current post to the comment
			new_comment.post = post
			# Save the comment to the database
			new_comment.save()
	else:
		comment_form = CommentForm()

	# list of similar posts
	post_tags_ids = post.tags.values_list('id', flat=True)
	similar_posts = Post.published.filter(tags__in=post_tags_ids)\
									.exclude(id=post.id)
	similar_posts = similar_posts.annotate(same_tags=Count('tags'))\
								.order_by('-same_tags','-publish')[:4]
	return render(request,
				'blog/post/detail.html',
				{'post': post,
				'comments': comments,
				'new_comment': new_comment,
				'comment_form': comment_form,
				'similar_posts': similar_posts})
				

def post_share(request, post_id):
	# retrieve post by id
	post = get_object_or_404(Post, id=post_id, status='published')
	sent = False
	if request.method == 'POST':
		# Form was submitted
		form = EmailPostForm(request.POST)
		if form.is_valid():
			# Form fields passed validation
			cd = form.cleaned_data
			# ... send email
			post_url = request.build_absolute_url(
									post.get_absolute_url())
			subject = '{} ({}) recommends you reading "{}"'.format(cd['name'], cd['email'], cd['comments'])
			message = 'Read "{}" at {}\n\n{}\'s comments: {}'.format(post.title, post_url, cd['name'], cd['comments'])
			send_mail(subject, message, 'admin@myblog',[cd['to']])
			sent = True
	else:
		form = EmailPostForm()

	return render(request, 'blog/post/share.html', {'post':post,
															'form': form,
															'sent': sent})