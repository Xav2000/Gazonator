from setuptools import find_packages, setup

package_name = 'mower_hardware'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
        'rclpy',
        'pyserial',
    ],
    zip_safe=True,
    maintainer='Xavier Rossignol',
    maintainer_email='xavier.rossignol@free.fr',
    description='Hardware interface package for the autonomous mower',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'motor_driver_node = mower_hardware.motor_driver_node:main',
        ],
    },
)