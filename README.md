[![Continous integration](https://github.com/frePPLe/frepple/actions/workflows/ubuntu20.yml/badge.svg)](https://github.com/frePPLe/frepple/actions/workflows/ubuntu20.yml)

# frePPLe

## BlackBytes

To build:

```sh
docker build -f contrib/docker/ubuntu-20.04.dockerfile -t prova-frepple .
```

To launch:

```sh
# start
docker-compose up -d

# stop
docker-compose down
```

To compile theme

```sh 
npx grunt sass
```




------------------------------------

## Open source supply chain planning

FrePPLe is an easy-to-use and easy-to-implement open source **advanced planning and scheduling** tool for manufacturing companies.

When spreadsheets doesn't suffice any longer to adequately plan and schedule your production, frePPLe allows an easy and cost-efficient way to generate a more optimized plan.

FrePPLe implements planning algoritms based on best practices such as **theory of constraints** (ie *plan around the bottleneck*), **pull-based planning** (ie *start production as late as possible and directly triggered by demand*) and **lean manufacturing** (ie *avoid intermediate delays and inventory*).

## Download

The software can be downloaded in the following formats:

* Ubuntu 20 .deb package on https://github.com/frePPLe/frepple/releases/
* Docker container on https://github.com/orgs/frePPLe/packages/container/package/frepple-community
* Source tarball or zip file from https://github.com/frePPLe/frepple/releases/
* Documentation zip file from https://github.com/frePPLe/frepple/releases/

## Documentation

Visit [https://frepple.com](https://frepple.com) for documentation, screencasts and build instructions.

## License

The *Community Edition* is released under the [GNU Affero General
Public License v3 or later](http://www.gnu.org/licenses/).

The *Enterprise Edition* can be purchased from frePPLe bv. It provides additional functionality
and professional support.

The *Cloud Edition* provides provides the same capabilities as the Enterprise Edition, but is
hosted as a service in the cloud: fully supported and maintained by frePPLe bv.
