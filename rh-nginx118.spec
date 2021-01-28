%global scl_name_prefix  rh-
%global scl_name_base    nginx
%global scl_name_version 118
%global scl              %{scl_name_prefix}%{scl_name_base}%{scl_name_version}
%{!?nfsmountable: %global nfsmountable 1}
%scl_package %scl

%{!?scl_perl:%global scl_perl rh-perl530}
%{!?scl_prefix_perl:%global scl_prefix_perl %{scl_perl}-}

# do not produce empty debuginfo package
%global debug_package %{nil}

%global nginx_perl_vendorarch %{_scl_root}%(eval "`%{_root_bindir}/perl -V:installvendorarch`"; echo $installvendorarch)
%global nginx_perl_archlib %{_scl_root}%(eval "`%{_root_bindir}/perl -V:archlib`"; echo $archlib)

Summary:       Package that installs %scl
Name:          %scl_name
Version:       1.18
Release:       7%{?dist}
License:       GPLv2+
Group: Applications/File
Source0: README
Source1: LICENSE
Source2: README.7

BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires: scl-utils-build
# Temporary work-around
BuildRequires: iso-codes

Requires: %{scl_prefix}nginx

%description
This is the main package for %scl Software Collection.

%package runtime
Summary:   Package that handles %scl Software Collection.
Requires:  scl-utils
Requires(post): policycoreutils-python libselinux-utils

%description runtime
Package shipping essential scripts to work with %scl Software Collection.

%package build
Summary:   Package shipping basic build configuration
Requires:  scl-utils-build
Requires: %{scl_prefix_perl}scldevel

%description build
Package shipping essential configuration macros to build %scl Software Collection.

%package scldevel
Summary:   Package shipping development files for %scl
Group:     Development/Languages

%description scldevel
Package shipping development files, especially usefull for development of
packages depending on %scl Software Collection.

%prep
%setup -c -T

# copy the license file so %%files section sees it
cp %{SOURCE0} .
cp %{SOURCE1} .
cp %{SOURCE2} .

expand_variables() {
    sed -i 's|%%{scl_name}|%{scl_name}|g' "$1"
    sed -i 's|%%{_scl_root}|%{_scl_root}|g' "$1"
    sed -i 's|%%{version}|%{version}|g' "$1"
%if 0%{?rhel} > 6
    sed -i 's|%%{service_start}|systemctl start %{scl_name}-nginx|g' "$1"
%else
    sed -i 's|%%{service_start}|service %{scl_name}-nginx start|g' "$1"
%endif
}

expand_variables README.7
expand_variables README

# Not required for now
#export LIBRARY_PATH=%{_libdir}\${LIBRARY_PATH:+:\${LIBRARY_PATH}}
#export LD_LIBRARY_PATH=%{_libdir}\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}

cat <<EOF | tee enable
if scl -l  | grep %{scl_perl} >&/dev/null; then
  . scl_source enable %{scl_perl}
fi
export PATH=%{_bindir}:%{_sbindir}\${PATH:+:\${PATH}}
export MANPATH=%{_mandir}:\${MANPATH}
export PKG_CONFIG_PATH=%{_libdir}/pkgconfig\${PKG_CONFIG_PATH:+:\${PKG_CONFIG_PATH}}
export PERL5LIB="%{nginx_perl_vendorarch}\${PERL5LIB:+:\${PERL5LIB}}"
EOF

# generate rpm macros file for depended collections
cat << EOF | tee scldev
%%scl_%{scl_name_base}         %{scl}
%%scl_prefix_%{scl_name_base}  %{scl_prefix}
EOF

%build

%install
mkdir -p %{buildroot}%{_scl_scripts}/root
install -m 644 enable  %{buildroot}%{_scl_scripts}/enable
install -D -m 644 scldev %{buildroot}%{_root_sysconfdir}/rpm/macros.%{scl_name_base}-scldevel

mkdir -p -m 755 \
      %{buildroot}%{_localstatedir}/run/ \
      %{buildroot}%{nginx_perl_vendorarch}

# install generated man page
mkdir -p %{buildroot}%{_mandir}/man7/
install -m 644 README.7 %{buildroot}%{_mandir}/man7/%{scl_name}.7

# workaround scl-utils bug #1487085
%ifarch ppc64le aarch64
install -d -m 755 %{buildroot}%{_scl_root}/usr/lib64
ln -s  usr/lib64  %{buildroot}%{_scl_root}/lib64
%endif

%scl_install

cat >> %{buildroot}%{_root_sysconfdir}/rpm/macros.%{scl}-config << EOF
%%scl_package_override() %%{expand:%%global __perl_requires /usr/lib/rpm/perl.req.rh-perl530 \
%%global __perl_provides /usr/lib/rpm/perl.prov.rh-perl530 \
%%global __perl %{_scl_prefix}/%{scl_perl}/root/usr/bin/perl \
%%global _nginx_perl_vendorarch %{nginx_perl_vendorarch} \
}
EOF

# create directory for SCL register scripts
mkdir -p %{buildroot}%{?_scl_scripts}/register.content
mkdir -p %{buildroot}%{?_scl_scripts}/register.d
cat <<EOF | tee %{buildroot}%{?_scl_scripts}/register
#!/bin/sh
ls %{?_scl_scripts}/register.d/* | while read file ; do
    [ -x \$f ] && source \$(readlink -f \$file)
done
EOF
# and deregister as well
mkdir -p %{buildroot}%{?_scl_scripts}/deregister.d
cat <<EOF | tee %{buildroot}%{?_scl_scripts}/deregister
#!/bin/sh
ls %{?_scl_scripts}/deregister.d/* | while read file ; do
    [ -x \$f ] && source \$(readlink -f \$file)
done
EOF

%post runtime
# Simple copy of context from system root to DSC root.
# In case new version needs some additional rules or context definition,
# it needs to be solved.
# Unfortunately, semanage does not have -e option in RHEL-5, so we have to
# have its own policy for collection
semanage fcontext -a -e / %{_scl_root} >/dev/null 2>&1 || :
restorecon -R %{_scl_root} >/dev/null 2>&1 || :
selinuxenabled && load_policy || :

%files

%files runtime
%defattr(-,root,root)
%doc README LICENSE
%scl_files
%dir %{_mandir}/man3
%dir %{_mandir}/man7
%dir %{_mandir}/man8
%{_mandir}/man7/%{scl_name}.*

%dir %{_localstatedir}/run
%dir %{nginx_perl_archlib}
%dir %{nginx_perl_vendorarch}

%attr(0755,root,root) %{?_scl_scripts}/register
%attr(0755,root,root) %{?_scl_scripts}/deregister
%{?_scl_scripts}/register.content
%dir %{?_scl_scripts}/register.d
%dir %{?_scl_scripts}/deregister.d
%ifarch ppc64le aarch64
%{_scl_root}/lib64
%{_scl_root}/usr/lib64
%endif

%files build
%defattr(-,root,root)
%{_root_sysconfdir}/rpm/macros.%{scl}-config

%files scldevel
%defattr(-,root,root)
%{_root_sysconfdir}/rpm/macros.%{scl_name_base}-scldevel

%changelog
* Wed Sep 16 2020 Lubos Uhliarik <luhliari@redhat.com> - 1.18-7
- Switch rh-nginx118 to rh-perl530

* Tue Jul 21 2020 Lubos Uhliarik <luhliari@redhat.com> - 1.18-1
- initial packaging
