from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views.generic import View, TemplateView, CreateView, FormView

from .forms import CheckoutForm, CustomerRegistrationForm, CustomerLoginForm
from django.urls import reverse_lazy
from .models import *


class EcomMixin(object):
    def dispatch(self, request, *args, **kwargs):
        cart_id = request.session.get('cart_id')
        if cart_id:
            cart_obj = Cart.objects.get(id=cart_id)
            if request.user.is_authenticated and request.user.customer:
                cart_obj.customer = request.user.customer
                cart_obj.save()

        return super().dispatch(request, *args, **kwargs)


class HomeView(EcomMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['my_name'] = "babita bista"
        context['product_list'] = Product.objects.all().order_by("-id")
        return context


class AllProductsView(EcomMixin, TemplateView):
    template_name = "all_products.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_categories'] = Category.objects.all()
        return context


class ProductDetailView(EcomMixin,TemplateView):
    template_name = "productdetail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        url_slug = kwargs['slug']
        product = Product.objects.get(slug=url_slug)
        product.view_count += 1
        product.save()
        context['product'] = product
        return context


class AddToCartView(EcomMixin, TemplateView):
    template_name = "addtocart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # get product id from requested url
        product_id = self.kwargs['product_id']

        # get product
        product_obj = Product.objects.get(id=product_id)

        # check if cart exists
        cart_id = self.request.session.get("cart_id", None)
        if cart_id:
            cart_obj = Cart.objects.get(id=cart_id)
            this_product_in_cart = cart_obj.cartproduct_set.filter(product=product_obj)

            # item already exists in cart
            if this_product_in_cart.exists():
                cartproduct = this_product_in_cart.last()
                cartproduct.quantity += 1
                cartproduct.subtotal += product_obj.selling_price
                cartproduct.save()
                cart_obj.total += product_obj.selling_price
                cartproduct.save()

            # new item added in cart
            else:
                cartproduct = CartProduct.objects.create(
                    cart = cart_obj, product=product_obj, rate=product_obj.selling_price, quantity=1, subtotal=product_obj.selling_price)
                cart_obj.total += product_obj.selling_price
                cart_obj.save()

        else:
            cart_obj = Cart.objects.create(total=0)

            # store the value immediately in session
            self.request.session['cart_id'] = cart_obj.id
            cartproduct = CartProduct.objects.create(
                cart=cart_obj, product=product_obj, rate=product_obj.selling_price, quantity=1,
                subtotal=product_obj.selling_price)
            cart_obj.total += product_obj.selling_price
            cart_obj.save()

        return context


class AboutView(EcomMixin, TemplateView):
    template_name = "about.html"


class ManageCartView(EcomMixin, View):
    def get(self, request, *args, **kwargs):
        # print("manage cart part")
        # to use dynamic id self.kwargs is used
        cp_id = self.kwargs['cp_id']
        #
        action = request.GET.get("action")
        cp_obj = CartProduct.objects.get(id=cp_id)
        cart_obj = cp_obj.cart
        # cart_obj.total = 0

        if action == "inc":
            cp_obj.quantity += 1
            cp_obj.subtotal += cp_obj.rate
            cp_obj.save()
            cart_obj.total += cp_obj.rate
            cart_obj.save()
        elif action == "dcr":
            cp_obj.quantity -= 1
            cp_obj.subtotal -= cp_obj.rate
            cp_obj.save()
            cart_obj.total -= cp_obj.rate
            cart_obj.save()
            if cp_obj.quantity <= 0:
                cp_obj.delete()
        elif action == "rmv":
            cart_obj.total -= cp_obj.subtotal
            cart_obj.save()
            cp_obj.delete()

        else:
            pass
        return redirect('ecomapp:mycart')


class EmptyCartView(EcomMixin, View):
    def get(self, request, *args, **kwargs):
        cart_id = request.session.get("cart_id", None)
        if cart_id:
            cart = Cart.objects.get(id=cart_id)
            cart.cartproduct_set.all().delete()
            cart.total = 0
            cart.save()
        return redirect("ecomapp:mycart")


class MyCartView(EcomMixin, TemplateView):
    template_name = "mycart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_id = self.request.session.get("cart_id", None)
        # cart1 = cp_obj.cart
        # cart_id = request.session.get("cart_id", None)
        if cart_id:
            cart = Cart.objects.get(id=cart_id)
        else:
            cart = None
        context['cart'] = cart
        return context


class CheckoutView(EcomMixin, CreateView):
    template_name = "checkout.html"
    form_class = CheckoutForm
    success_url = reverse_lazy('ecomapp:home')

    # dispatch run at the first or beginning before other method, check user is logged in or not
    # @method_decorator(auth_middleware, name='dispatch')
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.customer:
            # print('logged in user')
            pass
        else:
            # return redirect("/login")
            return redirect("/login/?next=/checkout/")
    #     #     # print("Not logged in user")
    #
        return super().dispatch(request, *args, **kwargs)

    # @method_decorator(auth_middleware, name='dispatch')
    # @login_required
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_id = self.request.session.get("cart_id", None)
        if cart_id:
            cart_obj = Cart.objects.get(id=cart_id)
        else:
            cart_obj = None
        context['cart'] = cart_obj
        return context

    def form_valid(self, form):
        cart_id = self.request.session.get('cart_id')
        if cart_id:
            cart_obj = Cart.objects.get(id=cart_id)
            form.instance.cart = cart_obj
            form.instance.subtotal = cart_obj.total
            form.instance.discount = 0
            form.instance.total = cart_obj.total
            form.instance.order_status = "Order Received"
            del self.request.session['cart_id']
        else:
            return redirect("ecomapp:home")
        return super().form_valid(form)


class ContactUsView(TemplateView):
    template_name = "contactUs.html"


class RegisterView(CreateView):
    template_name = "register.html"
    form_class = CustomerRegistrationForm
    success_url = reverse_lazy('ecomapp:home')

    # to handle form and available only in createview, updadteview, formview
    def form_valid(self, form):
        # grab data from query dictionary
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        email = form.cleaned_data.get('email')

        user = User.objects.create_user(username, password, email)
        form.instance.user = user
        # immediately login user after registration
        login(self.request, user)
        return super().form_valid(form)


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('ecomapp:home')


class LoginView(FormView):
    template_name = "login.html"
    form_class = CustomerLoginForm
    success_url = reverse_lazy('ecomapp:home')

    def form_valid(self, form):
        # grab data from query dict
        un = form.cleaned_data.get('username')
        pw = form.cleaned_data.get('password')

        user = authenticate( username=un, password=pw)
        if user is not None and user.customer:
            print('logged in')
            login(self.request, user)

        else:
            print('not logged in')
            # return render(self.request)
            return render(self.request, self.template_name, {"form": self.form_class, "error":"Invalid credential"})
        return super().form_valid(form)
