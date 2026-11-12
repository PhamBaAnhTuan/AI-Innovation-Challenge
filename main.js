document.addEventListener('DOMContentLoaded', () => {
  // Mobile Menu Toggle
  const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
  const navLinks = document.querySelector('.nav-links');
  
  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', () => {
      mobileMenuBtn.classList.toggle('active');
      navLinks.classList.toggle('active');
    });
  }

  // Close mobile menu when clicking a link
  const navItems = document.querySelectorAll('.nav-links a');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      if (navLinks.classList.contains('active')) {
        mobileMenuBtn.classList.remove('active');
        navLinks.classList.remove('active');
      }
    });
  });

  // Sticky Navbar on Scroll
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });

  // Scroll Reveal Animations
  const revealElements = document.querySelectorAll('.reveal');
  
  const revealCallback = (entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
        // observer.unobserve(entry.target); // Uncomment to only animate once
      }
    });
  };

  const revealOptions = {
    threshold: 0.15,
    rootMargin: "0px 0px -50px 0px"
  };

  const revealObserver = new IntersectionObserver(revealCallback, revealOptions);
  
  revealElements.forEach(el => {
    revealObserver.observe(el);
  });

  // Handle Form Submission
  const registerForm = document.getElementById('registerForm');
  const formSuccess = document.getElementById('formSuccess');
  const formError = document.getElementById('formError');
  const entryType = document.getElementById('entryType');
  const teamName = document.getElementById('teamName');
  const teamNameGroup = document.getElementById('teamNameGroup');

  if (registerForm && entryType && teamName && teamNameGroup && formSuccess && formError) {
    const memberGroups = [
      document.getElementById('member2Fields'),
      document.getElementById('member3Fields')
    ].filter(Boolean);

    const updateMemberFields = () => {
      const memberCount = Number(entryType.value);
      teamNameGroup.classList.toggle('hidden', memberCount === 1);
      teamName.required = memberCount > 1;

      memberGroups.forEach((group, index) => {
        const isVisible = memberCount > index + 1;
        group.classList.toggle('hidden', !isVisible);
        group.querySelectorAll('input').forEach(input => {
          input.disabled = !isVisible;
          input.required = isVisible;
        });
      });
    };

    updateMemberFields();
    entryType.addEventListener('change', updateMemberFields);

    registerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submitButton = registerForm.querySelector('button[type="submit"]');
      const originalButtonText = submitButton.textContent;

      submitButton.disabled = true;
      submitButton.textContent = 'Đang gửi đăng ký...';
      formError.classList.add('hidden');
      formError.textContent = '';

      try {
        const response = await fetch('/api/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(Object.fromEntries(new FormData(registerForm)))
        });
        const result = await response.json();

        if (!response.ok) {
          const message = Array.isArray(result.detail)
            ? result.detail.map(error => error.msg).join('; ')
            : result.detail;
          throw new Error(message || 'Không thể lưu đăng ký. Vui lòng thử lại.');
        }

        registerForm.classList.add('hidden');
        formSuccess.classList.remove('hidden');
        formSuccess.focus();
      } catch (error) {
        console.error('Không thể gửi đăng ký:', error);
        formError.textContent = error instanceof TypeError
          ? 'Không thể kết nối máy chủ. Vui lòng thử lại sau.'
          : error.message;
        formError.classList.remove('hidden');
        formError.focus();
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = originalButtonText;
      }
    });
  }

  // Add active state to nav links based on scroll position
  const sections = document.querySelectorAll('section[id]');
  
  window.addEventListener('scroll', () => {
    let current = '';
    
    sections.forEach(section => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.clientHeight;
      if (scrollY >= (sectionTop - 200)) {
        current = section.getAttribute('id');
      }
    });

    navItems.forEach(item => {
      item.classList.remove('active');
      if (item.getAttribute('href').includes(current)) {
        item.classList.add('active');
      }
    });
  });
});
