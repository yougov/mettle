Follow these steps to get a local copy of Mettle running.

1. Install [Vagrant](https://www.vagrantup.com/downloads.html).
2. Clone the repository at https://bitbucket.org/yougov/mettle.
3. From the root of the repository, type `vagrant up`.  Wait for the
provisioning script to finish.
4. Type `vagrant ssh` to get a shell into the Vagrant environment.
5. `cd /vagrant`
6. `mkvirtualenv mettle`
7. `make dev`.
8. `foreman start`

You should now see a bunch of output in your terminal.  The Mettle UI should be
running on port 8000, and some dummy jobs will be running (creating some tiny
text files in a temp folder).  You can click around the Mettle UI to watch those
jobs complete, or fail (they're coded to randomly fail some percent of the time,
so we can test retries and error reporting).
