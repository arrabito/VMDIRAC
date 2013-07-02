########################################################################
# $HeadURL$
# File :   OcciImage.py
# Author : Victor Mendez ( vmendez.tic@gmail.com )
########################################################################

# DIRAC
from DIRAC import gLogger, gConfig, S_OK, S_ERROR

# VMDIRAC
from VMDIRAC.WorkloadManagementSystem.Utilities.Configuration import OcciConfiguration, ImageConfiguration


__RCSID__ = '$Id: $'

class OcciImage:

  def __init__( self, imageName, endPoint):
    """
    The OCCI Image Interface provides the functionality required to use a standard occi cloud infrastructure.
    Constructor: uses OcciConfiguration to parse the endPoint CS configuration
    and ImageConfiguration to parse the imageName CS configuration.

    :Parameters:
      **imageName** - `string`
        imageName as defined on CS:/Resources/VirtualMachines/Images

      **endPoint** - `string`
        endPoint as defined on CS:/Resources/VirtualMachines/CloudEndpoint

    """
    # logger
    self.log       = gLogger.getSubLogger( 'OcciImage %s: ' % imageName )

    self.imageName = imageName
    self.endPoint  = endPoint

    # their config() method returns a dictionary with the parsed configuration
    # they also provide a validate() method to make sure it is correct
    self.__imageConfig = ImageConfiguration( imageName )
    self.__occiConfig  = OcciConfiguration( endPoint )

    # this object will connect to the server. Better keep it private.
    self.__cliocci   = None
    # error status of the image with the asociated context (endpoing + image), basically for check_connction propagation
    self.__errorStatus   = None

  def connectOcci( self ):
    """
    Method that issues the connection with the OpenNebula server. In order to do
    it, validates the CS configurations. 
    OcciClient which will check the connection.

    :return: S_OK | S_ERROR
    """

    # Before doing anything, make sure the configurations make sense
    # ImageConfiguration
    validImage = self.__imageConfig.validate()
    if not validImage[ 'OK' ]:
      return validImage
    # EndpointConfiguration
    validOcci = self.__occiConfig.validate()
    if not validOcci[ 'OK' ]:
      return validOcci

    # Get authentication configuration
    auth, u, p = self.__occiConfig.authConfig()
    if auth is 'userpasswd':
      user = u
      secret = p
    elif auth is 'proxycacert':
      userCredPath = u
      proxyCa = p
    else
      self.__errorStatus = "auth not supported" 
      self.log.error( self.__errorStatus )
      return

    # Create the occiclient objects in OcciClient:
    if self.__occiConfig.cloudDriver() == "occi-0.8":
      from VMDIRAC.WorkloadManagementSystem.Client.Occi08 import OcciClient
      self.__cliocci = OcciClient(user, secret, self.__occiConfig.config(), self.__imageConfig.config())
    elif self.__occiConfig.cloudDriver() == "occi-0.9":
      from VMDIRAC.WorkloadManagementSystem.Client.Occi09 import OcciClient
      self.__cliocci = OcciClient(user, secret, self.__occiConfig.config(), self.__imageConfig.config())
    elif self.__occiConfig.cloudDriver() == "occi-1.1":
      from VMDIRAC.WorkloadManagementSystem.Client.Occi11 import OcciClient
      self.__cliocci = OcciClient(userCredPath, proxyCaPath, self.__occiConfig.config(), self.__imageConfig.config())
    else:
      self.__errorStatus = "Driver %s not supported" % self.__cloudDriver
      self.log.error( self.__errorStatus )
      return

    # Check connection to the server
    request = self.__cliocci.check_connection()
    if request.returncode != 0:
      self.__errorStatus = "Can't connect to OCCI URI %s\n%s" % (self.__occiConfig.occiURI(), request.stdout)
      self.log.error( self.__errorStatus )
      return S_ERROR( self.__errorStatus )
    else:
      self.log.info( "Successful connection check to %s" % (self.__occiConfig.occiURI()) )

    return S_OK( request.stdout )

  def startNewInstance( self, cpuTime ):
    """
    Prior to use, virtual machine images are uploaded to the OCCI cloud manager assigned an id (OII in a URI). 
    """
    if self.__errorStatus:
      return S_ERROR( self.__errorStatus )

    self.log.info( "Starting new instance for DIRAC image (boot,hdc): %s; to endpoint %s" % ( self.imageName, self.endPoint) )
    request = self.__cliocci.create_VMInstance(cpuTime)
    if request.returncode != 0:
      self.__errorStatus = "Can't create instance for DIRAC image (boot,hdc): %s; to endpoint %s" % ( self.imageName, self.endPoint) 
      self.log.error( self.__errorStatus )
      return S_ERROR( self.__errorStatus )

    return S_OK( request.stdout )

  def stopInstance( self, VMinstanceId ):
    """
    Simple call to terminate a VM based on its id
    """

    request = self.__cliocci.terminate_VMinstance( VMinstanceId )
    if request.returncode != 0:
      self.__errorStatus = "Can't delete VM instance ide %s from endpoint URL %s\n%s" % (VMinstanceId, self.__occiConfig.occiURI(), request.stdout)
      self.log.error( self.__errorStatus )
      return S_ERROR( self.__errorStatus )

    return S_OK( request.stdout )


  def contextualizeInstance( self, uniqueId, public_ip ):
    """
    This method is not a regular method in the sense that is not generic at all.
    It will be called only of those VMs which need after-booting contextualisation,
    for the time being, just ssh contextualisation.
    On the other hand, one can say this is the most generic method because you don't
    need any particular "golden" image, like HEPiX, just whatever linux image with 
    available ssh connectivity

    :Parameters:
      **uniqueId** - `string`
        node ID, given by the OpenStack service
      **public_ip** - `string`
        public IP of the VM, needed for asynchronous contextualisation


    :return: S_OK | S_ERROR
    """

    # FIXME: maybe is worth hiding the public_ip attribute and getting it on
    # FIXME: the contextualize step.

    result = self.__cliocci.contextualize_VMInstance( uniqueId, public_ip )

    if not result[ 'OK' ]:
      self.log.error( "contextualizeInstance: %s, %s" % ( uniqueId, public_ip ) )
      self.log.error( result[ 'Message' ] )
      return result

    return S_OK( uniqueId )

#...............................................................................
#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF
